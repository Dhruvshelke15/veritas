import re
from dataclasses import dataclass

# Strong terms are specific enough that a single match makes an item relevant.
STRONG_TERMS: list[tuple[str, re.Pattern[str]]] = [
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in [
        ("optional practical training", r"\boptional practical training\b"),
        ("stem opt", r"\bstem[- ]opt\b"),
        ("cap-gap", r"\bcap[- ]gap\b"),
        ("f-1 students", r"\bf-1 students?\b"),
        ("practical training extension", r"\bpractical training extension\b"),
        ("curricular practical training", r"\bcurricular practical training\b"),
        ("day-1 cpt", r"\bday[- ]1 cpt\b"),
    ]
]

# Weak terms are common enough on their own that they need to accumulate
# before an item is treated as relevant (avoids flagging every H-1B or
# general immigration update as an OPT/F-1 change).
WEAK_TERMS: list[tuple[str, re.Pattern[str]]] = [
    (label, re.compile(pattern, re.IGNORECASE))
    for label, pattern in [
        ("student", r"\bstudents?\b"),
        ("employment authorization", r"\bemployment authorization\b"),
        ("opt", r"\bopt\b"),
        ("sevis", r"\bsevis\b"),
        ("form i-765", r"\bform i-765\b"),
        ("work authorization", r"\bwork authorization\b"),
        ("f-1", r"\bf-1\b"),
        ("h-1b", r"\bh-1b\b"),
    ]
]

WEAK_MATCH_THRESHOLD = 2


@dataclass(frozen=True)
class ScoredText:
    score: float
    matched: tuple[str, ...]
    is_relevant: bool


def score_text(text: str) -> ScoredText:
    strong_matched = [label for label, pattern in STRONG_TERMS if pattern.search(text)]
    weak_matched = [label for label, pattern in WEAK_TERMS if pattern.search(text)]

    score = len(strong_matched) * 1.0 + len(weak_matched) * 0.4
    is_relevant = len(strong_matched) >= 1 or len(weak_matched) >= WEAK_MATCH_THRESHOLD

    return ScoredText(score=score, matched=tuple(strong_matched + weak_matched), is_relevant=is_relevant)
