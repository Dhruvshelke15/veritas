from pathlib import Path

from app.classifier.dataset import CATEGORIES

MAX_TOKENS = 5000
SEQUENCE_LENGTH = 32
EMBEDDING_DIM = 64


def build_model(train_texts: list[str]):
    import tensorflow as tf

    vectorizer = tf.keras.layers.TextVectorization(
        max_tokens=MAX_TOKENS,
        output_mode="int",
        output_sequence_length=SEQUENCE_LENGTH,
    )
    vectorizer.adapt(train_texts)

    model = tf.keras.Sequential(
        [
            tf.keras.layers.Input(shape=(1,), dtype=tf.string),
            vectorizer,
            tf.keras.layers.Embedding(MAX_TOKENS, EMBEDDING_DIM),
            tf.keras.layers.GlobalAveragePooling1D(),
            tf.keras.layers.Dense(64, activation="relu"),
            tf.keras.layers.Dropout(0.3),
            tf.keras.layers.Dense(len(CATEGORIES), activation="softmax"),
        ]
    )
    model.compile(
        optimizer="adam",
        loss="sparse_categorical_crossentropy",
        metrics=["accuracy"],
    )
    return model


def save_model(model, path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    model.save(str(path))


def load_model(path: Path):
    import tensorflow as tf

    return tf.keras.models.load_model(str(path))
