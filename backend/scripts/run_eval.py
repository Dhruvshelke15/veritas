import argparse
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classifier.predictor import get_classifier
from app.config import settings
from app.eval.golden import load_golden_set
from app.eval.runner import run_eval
from app.rag.generator import get_generator


def main() -> None:
    parser = argparse.ArgumentParser(description="Run the Veritas evaluation harness")
    parser.add_argument("--golden-file", default=str(settings.golden_set_path))
    parser.add_argument("--db-file", default=str(settings.eval_db_path))
    parser.add_argument("--top-k", type=int, default=None)
    parser.add_argument("--no-classifier", action="store_true", help="Skip classifier routing/accuracy")
    args = parser.parse_args()

    questions = load_golden_set(Path(args.golden_file))
    print(f"Loaded {len(questions)} golden questions")

    classifier = None if args.no_classifier else get_classifier()
    if classifier is None and not args.no_classifier:
        print("No trained classifier found at classifier_model_path -- running without routing")

    generator = get_generator()
    report = run_eval(
        questions=questions,
        generator=generator,
        judge_generator=generator,
        classifier=classifier,
        top_k=args.top_k or settings.default_top_k,
        db_path=Path(args.db_file),
    )

    print(f"\nRun {report.run_id} complete.")
    hit_rate_str = f"{report.retrieval_hit_rate:.3f}" if report.retrieval_hit_rate is not None else "n/a"
    print(f"Retrieval hit rate: {hit_rate_str}")
    faithfulness_str = (
        f"{report.mean_faithfulness:.2f}/5" if report.mean_faithfulness is not None else "n/a"
    )
    print(f"Mean faithfulness: {faithfulness_str}")
    if report.classifier_accuracy is not None:
        print("Classifier accuracy by category:")
        for category, accuracy in sorted(report.classifier_accuracy.items()):
            print(f"  {category:>16}: {accuracy:.3f}")
    else:
        print("Classifier accuracy: n/a (no classifier)")


if __name__ == "__main__":
    main()
