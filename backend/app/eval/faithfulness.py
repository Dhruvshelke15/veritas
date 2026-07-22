import json
from dataclasses import dataclass

from app.eval.golden import GoldenQuestion
from app.rag.generator import Generator
from app.rag.parsing import AnswerParseError, extract_json_payload
from app.rag.pipeline import AskResult

JUDGE_SYSTEM_PROMPT = """You are a strict grader for a document-grounded question-answering system used by F-1 international students. You score one answer at a time on a 1-5 faithfulness scale.

Faithfulness means: every factual claim in the answer is actually supported by the cited source passages, and nothing important is invented. A correct refusal (declining to answer because the sources don't cover it) is fully faithful when the question expects a refusal.

Score:
5 - Fully grounded: every claim traces to the cited passages, or the system correctly refused when it should have.
4 - Grounded with a minor omission or imprecision that doesn't change the substance.
3 - Partially grounded: the core claim is supported but includes an unsupported or slightly incorrect detail.
2 - Mostly ungrounded: the answer drifts materially from what the cited passages say.
1 - Fabricated or contradicts the sources, or fails to refuse when it should have, or refuses when the sources clearly did contain the answer.

Respond with ONLY a JSON object, no markdown fences, in exactly this shape:
{"score": 1, "rationale": "one or two sentences"}"""


class FaithfulnessJudgeError(ValueError):
    pass


@dataclass(frozen=True)
class FaithfulnessScore:
    score: int
    rationale: str


def build_judge_prompt(question: GoldenQuestion, result: AskResult) -> str:
    cited_passages = (
        "\n".join(f'[{c.chunk_id}] {c.text}' for c in result.citations)
        if result.citations
        else "(none -- the system did not cite any passages)"
    )
    expectation = (
        "This question is expected to be REFUSED (the corpus does not contain the answer)."
        if question.expect_refusal
        else f"Reference answer (for context, not a template to match verbatim): {question.reference_answer}"
    )
    return f"""Question: {question.query}

{expectation}

System's answer: {result.answer}
System marked sufficient_context as: {result.sufficient_context}

Cited passages:
{cited_passages}"""


def judge_faithfulness(
    question: GoldenQuestion, result: AskResult, generator: Generator
) -> FaithfulnessScore:
    raw = generator.generate(JUDGE_SYSTEM_PROMPT, build_judge_prompt(question, result))
    try:
        payload = extract_json_payload(raw)
        data = json.loads(payload)
    except (AnswerParseError, json.JSONDecodeError) as exc:
        raise FaithfulnessJudgeError(f"Unparseable judge output: {exc}") from exc

    score = data.get("score")
    rationale = data.get("rationale")
    if not isinstance(score, int) or not (1 <= score <= 5):
        raise FaithfulnessJudgeError(f"Invalid or missing 'score': {score!r}")
    if not isinstance(rationale, str) or not rationale.strip():
        raise FaithfulnessJudgeError("Missing or empty 'rationale'")

    return FaithfulnessScore(score=score, rationale=rationale.strip())
