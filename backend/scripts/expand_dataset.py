import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from anthropic import Anthropic

from app.classifier.dataset import (
    CATEGORIES,
    DatasetError,
    LabeledQuery,
    dedupe,
    label_counts,
    load_dataset,
    parse_generation_batch,
    save_dataset,
)
from app.config import settings

CATEGORY_DESCRIPTIONS = {
    "factual": "Questions asking for a specific fact, rule, definition, number, or deadline that official F-1/OPT/STEM OPT/cap-gap policy documents state directly. The answer is a lookup, not a judgment.",
    "procedural": "Questions asking how to do something: steps, processes, filing procedures, reporting requirements, or the order of actions related to F-1/OPT/STEM OPT/cap-gap.",
    "advice_seeking": "Questions asking for judgment, prediction, or a recommendation about the asker's specific situation. Markers include 'should I', 'will my', 'is it risky', 'what are my chances', case details, or requests to evaluate their eligibility. Topic is F-1/OPT/STEM OPT/cap-gap but the answer requires case-specific judgment no document provides.",
    "out_of_scope": "Questions the corpus cannot answer: other visa categories (H-4, B-2, O-1, L-1, TN, EB-5, green card, asylum, citizenship), taxes, general knowledge, chit-chat, or anything unrelated to F-1 student-to-work pathways.",
}

STYLE_INSTRUCTIONS = """Vary the style realistically: some formal and complete, some lowercase informal, some with minor typos, some terse (3-6 words), some long with background details. Write like real international students typing into a search box or chat, not like a textbook."""

BATCH_SIZE = 25
EXAMPLES_PER_PROMPT = 12


def build_prompt(label: str, examples: list[LabeledQuery], batch_size: int) -> str:
    example_lines = "\n".join(f"- {e.query}" for e in examples)
    return f"""You are generating training data for a query intent classifier in an F-1 student immigration information system.

Category: {label}
Definition: {CATEGORY_DESCRIPTIONS[label]}

Examples of this category:
{example_lines}

Generate {batch_size} NEW queries that belong to this category. Do not repeat or trivially rephrase the examples. {STYLE_INSTRUCTIONS}

Every query MUST unambiguously belong to the category "{label}" per the definition above. Avoid boundary cases that could plausibly fit another category.

Respond with ONLY a JSON object, no markdown fences, in exactly this shape:
{{"queries": ["query one", "query two"]}}"""


def expand_category(
    client: Anthropic,
    label: str,
    seeds: list[LabeledQuery],
    target: int,
    existing: list[LabeledQuery],
    rng: random.Random,
) -> list[LabeledQuery]:
    category_seeds = [s for s in seeds if s.label == label]
    collected: list[LabeledQuery] = []
    attempts = 0
    max_attempts = (target // BATCH_SIZE + 2) * 2

    while len(collected) < target and attempts < max_attempts:
        attempts += 1
        examples = rng.sample(category_seeds, min(EXAMPLES_PER_PROMPT, len(category_seeds)))
        prompt = build_prompt(label, examples, BATCH_SIZE)
        response = client.messages.create(
            model=settings.anthropic_model,
            max_tokens=2048,
            messages=[{"role": "user", "content": prompt}],
        )
        raw = "".join(block.text for block in response.content if block.type == "text")
        try:
            batch = parse_generation_batch(raw, label)
        except DatasetError as exc:
            print(f"  [{label}] batch {attempts} unparseable, skipping: {exc}")
            continue
        fresh = dedupe(batch, existing=existing + collected)
        collected.extend(fresh[: target - len(collected)])
        print(f"  [{label}] batch {attempts}: +{len(fresh)} new, {len(collected)}/{target}")

    return collected


def main() -> None:
    parser = argparse.ArgumentParser(description="Expand classifier seed dataset with Claude")
    parser.add_argument("--seed-file", default="../data/classifier/seed_queries.jsonl")
    parser.add_argument("--out-file", default="../data/classifier/expanded_queries.jsonl")
    parser.add_argument("--per-category", type=int, default=175)
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()

    seed_path = Path(args.seed_file)
    out_path = Path(args.out_file)
    seeds = load_dataset(seed_path)
    print(f"Loaded {len(seeds)} seed queries: {label_counts(seeds)}")

    client = Anthropic()
    rng = random.Random(args.random_seed)

    all_rows = list(seeds)
    for label in CATEGORIES:
        print(f"Expanding {label}...")
        generated = expand_category(client, label, seeds, args.per_category, all_rows, rng)
        all_rows.extend(generated)

    rng.shuffle(all_rows)
    save_dataset(all_rows, out_path)
    print(f"\nWrote {len(all_rows)} queries to {out_path}")
    print(f"Final distribution: {label_counts(all_rows)}")


if __name__ == "__main__":
    main()
