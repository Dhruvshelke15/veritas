from dataclasses import dataclass

from app.classifier.predictor import Classification
from app.config import settings

OUT_OF_SCOPE_ANSWER = "This system answers questions about F-1 student work pathways: OPT, STEM OPT, cap-gap, and the H-1B transition, using official USCIS and ICE sources. Your question appears to be outside that scope. For other immigration topics, see uscis.gov."

ADVICE_DISCLAIMER = "\n\nNote: this response provides information from official sources, not legal advice. Decisions about your specific situation are best made with your DSO or an immigration attorney."


@dataclass(frozen=True)
class RoutingDecision:
    action: str
    category: str | None
    confidence: float | None


def route(classification: Classification | None) -> RoutingDecision:
    if classification is None:
        return RoutingDecision(action="standard", category=None, confidence=None)
    if (
        classification.label == "out_of_scope"
        and classification.confidence >= settings.classifier_reject_threshold
    ):
        return RoutingDecision(
            action="reject", category=classification.label, confidence=classification.confidence
        )
    if classification.label == "advice_seeking":
        return RoutingDecision(
            action="advise", category=classification.label, confidence=classification.confidence
        )
    return RoutingDecision(
        action="standard", category=classification.label, confidence=classification.confidence
    )
