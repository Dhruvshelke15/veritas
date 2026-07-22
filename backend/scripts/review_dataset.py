import argparse
import random
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classifier.dataset import CATEGORIES, label_counts, load_dataset


def main() -> None:
    parser = argparse.ArgumentParser(description="Print a stratified sample for label review")
    parser.add_argument("--file", default="../data/classifier/expanded_queries.jsonl")
    parser.add_argument("--per-category", type=int, default=15)
    parser.add_argument("--random-seed", type=int, default=None)
    args = parser.parse_args()

    rows = load_dataset(Path(args.file))
    print(f"Total: {len(rows)}, distribution: {label_counts(rows)}\n")

    rng = random.Random(args.random_seed)
    for label in CATEGORIES:
        subset = [r for r in rows if r.label == label]
        sample = rng.sample(subset, min(args.per_category, len(subset)))
        print(f"=== {label} ({len(subset)} total) ===")
        for row in sample:
            print(f"  {row.query}")
        print()


if __name__ == "__main__":
    main()
