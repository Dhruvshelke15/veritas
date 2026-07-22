import argparse
import random
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.classifier.dataset import CATEGORIES, LabeledQuery, load_dataset
from app.classifier.model import build_model, save_model


def stratified_split(
    rows: list[LabeledQuery], seed: int, train_frac: float = 0.7, val_frac: float = 0.15
) -> tuple[list[LabeledQuery], list[LabeledQuery], list[LabeledQuery]]:
    rng = random.Random(seed)
    by_label: dict[str, list[LabeledQuery]] = defaultdict(list)
    for row in rows:
        by_label[row.label].append(row)

    train: list[LabeledQuery] = []
    val: list[LabeledQuery] = []
    test: list[LabeledQuery] = []
    for label in CATEGORIES:
        subset = list(by_label[label])
        rng.shuffle(subset)
        n_train = int(len(subset) * train_frac)
        n_val = int(len(subset) * val_frac)
        train.extend(subset[:n_train])
        val.extend(subset[n_train : n_train + n_val])
        test.extend(subset[n_train + n_val :])

    rng.shuffle(train)
    rng.shuffle(val)
    rng.shuffle(test)
    return train, val, test


def print_report(y_true: list[int], y_pred: list[int]) -> float:
    matrix = [[0] * len(CATEGORIES) for _ in CATEGORIES]
    for true, pred in zip(y_true, y_pred):
        matrix[true][pred] += 1

    print("\nConfusion matrix (rows=true, cols=predicted):")
    header = " " * 16 + "".join(f"{c[:8]:>10}" for c in CATEGORIES)
    print(header)
    for i, label in enumerate(CATEGORIES):
        print(f"{label:>15} " + "".join(f"{matrix[i][j]:>10}" for j in range(len(CATEGORIES))))

    print("\nPer-class metrics:")
    for i, label in enumerate(CATEGORIES):
        tp = matrix[i][i]
        fn = sum(matrix[i]) - tp
        fp = sum(matrix[j][i] for j in range(len(CATEGORIES))) - tp
        precision = tp / (tp + fp) if tp + fp else 0.0
        recall = tp / (tp + fn) if tp + fn else 0.0
        f1 = 2 * precision * recall / (precision + recall) if precision + recall else 0.0
        print(f"  {label:>15}: precision={precision:.3f} recall={recall:.3f} f1={f1:.3f}")

    accuracy = sum(matrix[i][i] for i in range(len(CATEGORIES))) / len(y_true)
    print(f"\nOverall accuracy: {accuracy:.3f} ({len(y_true)} examples)")
    return accuracy


def main() -> None:
    parser = argparse.ArgumentParser(description="Train the query intent classifier")
    parser.add_argument("--data-file", default="../data/classifier/expanded_queries.jsonl")
    parser.add_argument("--model-out", default="../data/classifier/model.keras")
    parser.add_argument("--epochs", type=int, default=40)
    parser.add_argument("--random-seed", type=int, default=42)
    args = parser.parse_args()

    import numpy as np
    import tensorflow as tf

    tf.random.set_seed(args.random_seed)
    np.random.seed(args.random_seed)

    rows = load_dataset(Path(args.data_file))
    train, val, test = stratified_split(rows, seed=args.random_seed)
    print(f"Split: train={len(train)} val={len(val)} test={len(test)}")

    label_to_index = {label: i for i, label in enumerate(CATEGORIES)}

    def to_arrays(subset: list[LabeledQuery]):
        return (
            tf.constant([r.query for r in subset]),
            np.array([label_to_index[r.label] for r in subset]),
        )

    x_train, y_train = to_arrays(train)
    x_val, y_val = to_arrays(val)
    x_test, y_test = to_arrays(test)

    model = build_model([r.query for r in train])
    early_stop = tf.keras.callbacks.EarlyStopping(
        monitor="val_loss", patience=5, restore_best_weights=True
    )
    model.fit(
        x_train,
        y_train,
        validation_data=(x_val, y_val),
        epochs=args.epochs,
        batch_size=32,
        callbacks=[early_stop],
        verbose=2,
    )

    probs = model.predict(x_test, verbose=0)
    y_pred = probs.argmax(axis=1).tolist()
    accuracy = print_report(y_test.tolist(), y_pred)

    save_model(model, Path(args.model_out))
    print(f"\nModel saved to {args.model_out}")

    if accuracy < 0.85:
        print("WARNING: test accuracy below 0.85, review before wiring into routing")


if __name__ == "__main__":
    main()
