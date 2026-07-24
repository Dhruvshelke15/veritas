import re
from datetime import date
from urllib.parse import urljoin, urlparse

from bs4 import BeautifulSoup
from bs4.element import Tag

from app.watch.models import RawItem

BASE_URL = "https://www.uscis.gov"

# The date is encoded in the filename itself, e.g.
# /sites/default/files/document/policy-manual-updates/20251127-Discretion.pdf
# This survives markup/CSS redesigns in a way selectors don't.
POLICY_PDF_HREF_RE = re.compile(
    r"/sites/default/files/document/policy-manual-updates/(\d{8})-([A-Za-z0-9\-]+)\.pdf"
)

ALERT_PATH_RE = re.compile(r"^/newsroom/alerts/[a-z0-9][a-z0-9\-]*/?$")

_MONTH_NAMES = [
    "january",
    "february",
    "march",
    "april",
    "may",
    "june",
    "july",
    "august",
    "september",
    "october",
    "november",
    "december",
]
_TEXT_DATE_RE = re.compile(rf"\b({'|'.join(_MONTH_NAMES)})\s+(\d{{1,2}}),?\s+(\d{{4}})\b", re.IGNORECASE)

# The Policy Manual listing's link text is a generic "Read More" — the real
# title only appears in the item body, as "POLICY ALERT - <title> <date>".
_GENERIC_LINK_TEXT = {"read more", "learn more", "view", "download", "view pdf"}
_POLICY_ALERT_TITLE_RE = re.compile(
    rf"POLICY ALERT\s*-\s*(.+?)\s+(?:{'|'.join(_MONTH_NAMES)})\s+\d{{1,2}},?\s+\d{{4}}",
    re.IGNORECASE,
)


def _extract_policy_alert_title(summary: str) -> str | None:
    match = _POLICY_ALERT_TITLE_RE.search(summary)
    return match.group(1).strip() if match else None


def _absolutize(href: str) -> str:
    if href.startswith("http://") or href.startswith("https://"):
        return href
    return urljoin(BASE_URL, href)


def _path_only(href: str) -> str:
    return urlparse(href).path


def _slug_to_title(slug: str) -> str:
    return slug.replace("-", " ").replace("_", " ").strip().title()


def _parse_yyyymmdd(raw: str) -> date | None:
    try:
        return date(int(raw[:4]), int(raw[4:6]), int(raw[6:8]))
    except ValueError:
        return None


def _parse_text_date(text: str) -> date | None:
    match = _TEXT_DATE_RE.search(text)
    if not match:
        return None
    month_name, day, year = match.groups()
    try:
        return date(int(year), _MONTH_NAMES.index(month_name.lower()) + 1, int(day))
    except ValueError:
        return None


def _containing_item(anchor: Tag, href_matches: re.Pattern[str] | None = None, *, max_levels: int = 4) -> Tag:
    """Climb from an anchor toward its listing-item wrapper, but stop as soon
    as the current container holds more than one candidate link — that means
    we've reached the shared list container rather than this item's own
    wrapper, and climbing further would pull in neighboring items' text.
    """
    node: Tag = anchor
    for _ in range(max_levels):
        parent = node.parent
        if parent is None or not isinstance(parent, Tag):
            break
        candidate_links = [
            a
            for a in parent.find_all("a", href=True)
            if href_matches is None or href_matches.search(a["href"])
        ]
        if len(candidate_links) > 1:
            break
        node = parent
    return node


def parse_policy_manual_updates(html: str) -> list[RawItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[RawItem] = []
    seen_hrefs: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        match = POLICY_PDF_HREF_RE.search(href)
        if not match or href in seen_hrefs:
            continue
        seen_hrefs.add(href)

        date_str, slug = match.group(1), match.group(2)
        published = _parse_yyyymmdd(date_str)

        container = _containing_item(anchor, POLICY_PDF_HREF_RE)
        summary = container.get_text(" ", strip=True)

        link_text = anchor.get_text(strip=True)
        title = link_text if link_text.lower() not in _GENERIC_LINK_TEXT else ""
        title = title or _extract_policy_alert_title(summary) or _slug_to_title(slug)

        items.append(
            RawItem(
                url=_absolutize(href),
                title=title,
                published=published,
                summary=summary,
                source="policy_manual",
            )
        )

    return items


def parse_alerts(html: str) -> list[RawItem]:
    soup = BeautifulSoup(html, "html.parser")
    items: list[RawItem] = []
    seen_hrefs: set[str] = set()

    for anchor in soup.find_all("a", href=True):
        href = anchor["href"]
        if not ALERT_PATH_RE.match(_path_only(href)) or href in seen_hrefs:
            continue
        title = anchor.get_text(strip=True)
        if not title:
            continue
        seen_hrefs.add(href)

        container = _containing_item(anchor, ALERT_PATH_RE)

        published = None
        time_tag = container.find("time")
        if time_tag is not None and time_tag.get("datetime"):
            try:
                published = date.fromisoformat(time_tag["datetime"][:10])
            except ValueError:
                published = None
        if published is None:
            published = _parse_text_date(container.get_text(" ", strip=True))

        summary = container.get_text(" ", strip=True)

        items.append(
            RawItem(
                url=_absolutize(href),
                title=title,
                published=published,
                summary=summary,
                source="alerts",
            )
        )

    return items
