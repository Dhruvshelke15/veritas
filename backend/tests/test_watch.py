from datetime import date
from pathlib import Path

import httpx
import pytest

from app.watch.fetch import FetchError, fetch_html
from app.watch.parsers import parse_alerts, parse_policy_manual_updates
from app.watch.scan import WatchParseError, run_scan
from app.watch.scoring import score_text
from app.watch.state import load_seen, save_seen

FIXTURES = Path(__file__).parent / "fixtures" / "watch"


def read_fixture(name: str) -> str:
    return (FIXTURES / name).read_text()


# --- scoring -----------------------------------------------------------


def test_strong_term_alone_is_relevant():
    scored = score_text("USCIS updates guidance on Optional Practical Training for graduates.")
    assert scored.is_relevant
    assert "optional practical training" in scored.matched


def test_single_weak_term_is_not_enough():
    scored = score_text("This update concerns student visa interview scheduling.")
    assert not scored.is_relevant


def test_two_weak_terms_accumulate_to_relevant():
    scored = score_text("Students must maintain valid work authorization at all times.")
    assert scored.is_relevant
    assert len(scored.matched) >= 2


def test_opt_word_boundary_avoids_false_positives():
    scored = score_text("The court adopted a new evidentiary standard for the hearing.")
    assert not scored.is_relevant
    assert "opt" not in scored.matched

    scored = score_text("The agency proposed an optional approach to committee review.")
    assert not scored.is_relevant
    assert "opt" not in scored.matched


# --- parsers -------------------------------------------------------------


def test_parse_policy_manual_updates_extracts_items():
    items = parse_policy_manual_updates(read_fixture("policy_manual_updates.html"))
    assert len(items) == 3

    discretion = next(i for i in items if "Discretion" in i.url)
    assert discretion.published == date(2025, 11, 27)
    assert discretion.title == "Update to Chapter 5: Discretion"
    assert discretion.url == (
        "https://www.uscis.gov/sites/default/files/document/policy-manual-updates/20251127-Discretion.pdf"
    )
    assert discretion.source == "policy_manual"


def test_parse_policy_manual_updates_does_not_bleed_neighboring_summaries():
    """Regression test: summary extraction must stop climbing once it hits a
    container with more than one candidate link, otherwise an unrelated item
    inherits its OPT-related neighbor's text and false-positives as relevant.
    """
    items = parse_policy_manual_updates(read_fixture("policy_manual_updates.html"))
    trafficking = next(i for i in items if "TraffickingVictims" in i.url)

    assert "practical training" not in trafficking.summary.lower()
    assert "opt" not in trafficking.summary.lower()
    assert not score_text(f"{trafficking.title} {trafficking.summary}").is_relevant


def test_parse_alerts_extracts_items_and_dates():
    items = parse_alerts(read_fixture("alerts.html"))
    assert len(items) == 3

    stem_alert = next(i for i in items if "stem-opt" in i.url)
    assert stem_alert.published == date(2026, 6, 20)
    assert stem_alert.source == "alerts"


def test_parse_returns_empty_list_on_unrelated_markup():
    assert parse_policy_manual_updates(read_fixture("blocked.html")) == []
    assert parse_alerts(read_fixture("blocked.html")) == []


# --- scan orchestration ----------------------------------------------------


def test_run_scan_finds_relevant_items_from_both_sources():
    result = run_scan(
        policy_manual_html=read_fixture("policy_manual_updates.html"),
        alerts_html=read_fixture("alerts.html"),
        seen_urls=set(),
    )
    assert result.policy_manual_count == 3
    assert result.alerts_count == 3
    # Trafficking Victims and Naturalization Civics Test are the two irrelevant items.
    assert len(result.all_relevant_items) == 4
    assert len(result.new_items) == 4


def test_run_scan_dedupes_against_seen_urls():
    first = run_scan(
        policy_manual_html=read_fixture("policy_manual_updates.html"),
        alerts_html=read_fixture("alerts.html"),
        seen_urls=set(),
    )
    already_seen = {first.all_relevant_items[0].url}

    second = run_scan(
        policy_manual_html=read_fixture("policy_manual_updates.html"),
        alerts_html=read_fixture("alerts.html"),
        seen_urls=already_seen,
    )
    assert len(second.all_relevant_items) == len(first.all_relevant_items)
    assert len(second.new_items) == len(first.all_relevant_items) - 1
    assert already_seen.isdisjoint({i.url for i in second.new_items})


def test_run_scan_since_days_filters_older_items():
    result = run_scan(
        policy_manual_html=read_fixture("policy_manual_updates.html"),
        alerts_html=read_fixture("alerts.html"),
        seen_urls=set(),
        since_days=3,
        today=date(2026, 6, 21),
    )
    # Only the STEM OPT alert (published 2026-06-20, 1 day before "today") is
    # within a 3-day window; the other relevant items (Nov 2025, Jun 15, Jun 10)
    # all fall outside it.
    assert len(result.new_items) == 1
    assert "stem-opt" in result.new_items[0].url


def test_run_scan_raises_on_zero_items_from_both_sources():
    with pytest.raises(WatchParseError):
        run_scan(
            policy_manual_html=read_fixture("blocked.html"),
            alerts_html=read_fixture("blocked.html"),
            seen_urls=set(),
        )


def test_run_scan_succeeds_if_only_one_source_yields_items():
    result = run_scan(
        policy_manual_html=read_fixture("policy_manual_updates.html"),
        alerts_html=read_fixture("blocked.html"),
        seen_urls=set(),
    )
    assert result.policy_manual_count == 3
    assert result.alerts_count == 0


# --- state -----------------------------------------------------------------


def test_load_seen_returns_empty_set_when_file_missing(tmp_path):
    assert load_seen(tmp_path / "does_not_exist.json") == set()


def test_save_and_load_seen_round_trip(tmp_path):
    path = tmp_path / "nested" / "seen.json"
    save_seen(path, {"https://example.com/a", "https://example.com/b"})
    assert load_seen(path) == {"https://example.com/a", "https://example.com/b"}


# --- fetch -------------------------------------------------------------


def test_fetch_html_returns_body_on_success():
    def handler(request: httpx.Request) -> httpx.Response:
        assert "Mozilla" in request.headers["user-agent"]
        return httpx.Response(200, text="<html>ok</html>")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    assert fetch_html("https://example.com", client=client) == "<html>ok</html>"


def test_fetch_html_raises_fetch_error_on_http_status_error():
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(403, text="blocked")

    client = httpx.Client(transport=httpx.MockTransport(handler))
    with pytest.raises(FetchError):
        fetch_html("https://example.com", client=client)
