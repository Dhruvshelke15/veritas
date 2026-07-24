from dataclasses import dataclass
from datetime import date


@dataclass(frozen=True)
class RawItem:
    url: str
    title: str
    published: date | None
    summary: str
    source: str


@dataclass(frozen=True)
class DiscoveredItem:
    url: str
    title: str
    published: date | None
    source: str
    score: float
    matched_keywords: tuple[str, ...]
