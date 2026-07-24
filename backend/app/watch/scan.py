from dataclasses import dataclass
from datetime import date

from app.watch.models import DiscoveredItem
from app.watch.parsers import parse_alerts, parse_policy_manual_updates
from app.watch.scoring import score_text


class WatchParseError(RuntimeError):
    """Raised when both sources parse to zero items.

    Silence is treated as failure: a monitoring tool that quietly reports
    "no updates found" when it actually failed to parse the page (markup
    drift, a bot-detection interstitial, ...) is worse than no tool at all,
    because it looks healthy while telling you nothing.
    """


@dataclass(frozen=True)
class ScanResult:
    new_items: list[DiscoveredItem]
    all_relevant_items: list[DiscoveredItem]
    policy_manual_count: int
    alerts_count: int


def run_scan(
    *,
    policy_manual_html: str,
    alerts_html: str,
    seen_urls: set[str],
    since_days: int | None = None,
    today: date | None = None,
) -> ScanResult:
    today = today or date.today()

    policy_raw = parse_policy_manual_updates(policy_manual_html)
    alerts_raw = parse_alerts(alerts_html)

    if not policy_raw and not alerts_raw:
        raise WatchParseError(
            "Parsed zero items from both the Policy Manual updates page and the "
            "alerts page. This usually means USCIS changed their markup or "
            "blocked the request (bot detection) rather than that there is "
            "genuinely nothing posted."
        )

    relevant: list[DiscoveredItem] = []
    for raw in policy_raw + alerts_raw:
        scored = score_text(f"{raw.title} {raw.summary}")
        if not scored.is_relevant:
            continue
        if since_days is not None and raw.published is not None:
            if (today - raw.published).days > since_days:
                continue
        relevant.append(
            DiscoveredItem(
                url=raw.url,
                title=raw.title,
                published=raw.published,
                source=raw.source,
                score=scored.score,
                matched_keywords=scored.matched,
            )
        )

    new_items = [item for item in relevant if item.url not in seen_urls]

    return ScanResult(
        new_items=new_items,
        all_relevant_items=relevant,
        policy_manual_count=len(policy_raw),
        alerts_count=len(alerts_raw),
    )
