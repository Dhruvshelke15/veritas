import argparse
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.watch.fetch import DEFAULT_USER_AGENT, FetchError, fetch_html
from app.watch.models import DiscoveredItem
from app.watch.scan import WatchParseError, run_scan
from app.watch.state import load_seen, save_seen

POLICY_MANUAL_UPDATES_URL = "https://www.uscis.gov/policy-manual/updates"
ALERTS_URL = "https://www.uscis.gov/newsroom/alerts"

DEFAULT_STATE_PATH = Path(__file__).resolve().parents[2] / "data" / "watch" / "seen.json"


def _item_dict(item: DiscoveredItem) -> dict:
    return {
        "url": item.url,
        "title": item.title,
        "published": item.published.isoformat() if item.published else None,
        "source": item.source,
        "score": item.score,
        "matched_keywords": list(item.matched_keywords),
    }


def _print_markdown(items: list[DiscoveredItem]) -> None:
    for item in items:
        published = item.published.isoformat() if item.published else "unknown"
        print(f"- **[{item.title}]({item.url})**")
        print(f"  - source: `{item.source}` | published: {published} | score: {item.score:.1f}")
        print(f"  - matched: {', '.join(item.matched_keywords)}")


def _print_text(result_new: list[DiscoveredItem], policy_count: int, alerts_count: int, total_relevant: int) -> None:
    print(f"Scanned {policy_count} policy manual updates, {alerts_count} alerts.")
    print(f"{total_relevant} relevant, {len(result_new)} new since last run.")
    for item in result_new:
        published = item.published.isoformat() if item.published else "unknown"
        print(f"\n[{item.source}] {item.title}")
        print(f"  {item.url}")
        print(f"  published: {published} | score: {item.score:.1f} | matched: {', '.join(item.matched_keywords)}")


def main() -> None:
    parser = argparse.ArgumentParser(description="Scan USCIS for new F-1/OPT-relevant guidance updates")
    parser.add_argument("--policy-url", default=POLICY_MANUAL_UPDATES_URL)
    parser.add_argument("--alerts-url", default=ALERTS_URL)
    parser.add_argument("--state-file", type=Path, default=DEFAULT_STATE_PATH)
    parser.add_argument("--since-days", type=int, default=None, help="Only report items published within N days")
    parser.add_argument("--json", action="store_true", help="Print new items as a JSON array")
    parser.add_argument("--markdown", action="store_true", help="Print new items as a Markdown list")
    parser.add_argument("--no-save-state", action="store_true", help="Don't update the seen-items state file")
    parser.add_argument("--user-agent", default=DEFAULT_USER_AGENT)
    args = parser.parse_args()

    try:
        policy_html = fetch_html(args.policy_url, user_agent=args.user_agent)
        alerts_html = fetch_html(args.alerts_url, user_agent=args.user_agent)
    except FetchError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    seen = load_seen(args.state_file)

    try:
        result = run_scan(
            policy_manual_html=policy_html,
            alerts_html=alerts_html,
            seen_urls=seen,
            since_days=args.since_days,
        )
    except WatchParseError as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        sys.exit(1)

    if args.json:
        print(json.dumps([_item_dict(i) for i in result.new_items], indent=2))
    elif args.markdown:
        _print_markdown(result.new_items)
    else:
        _print_text(result.new_items, result.policy_manual_count, result.alerts_count, len(result.all_relevant_items))

    if not args.no_save_state:
        all_relevant_urls = seen | {i.url for i in result.all_relevant_items}
        save_seen(args.state_file, all_relevant_urls)


if __name__ == "__main__":
    main()
