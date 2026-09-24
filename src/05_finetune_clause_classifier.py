import json
import os

import numpy as np
import pandas as pd

from datasets import Dataset
from sklearn.metrics import accuracy_score, precision_recall_fscore_support

from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)


# ============================================================
# CONFIGURATION
# ============================================================

MODEL_NAME = "nlpaueb/legal-bert-base-uncased"

DATA_DIR = "data/processed"
OUT_DIR = "models/clause_classifier"

TEXT_COL = "clause"
LABEL_COL = "label"

# ------------------------------------------------------------
# QUICK MODE
# ------------------------------------------------------------
# True  = small smoke test
# False = full training
#
# Since your machine is CPU-only, leave this TRUE locally.
# For the final model, run full training on Colab GPU.
# ------------------------------------------------------------

QUICK_MODE = True

QUICK_TRAIN_ROWS = 2000
QUICK_VAL_ROWS = 400
QUICK_EPOCHS = 1

FULL_EPOCHS = 4


# ============================================================
# LOAD LABEL MAPPING
# ============================================================

def load_label_mapping():
    label_path = os.path.join(
        DATA_DIR,
        "label_map.json"
    )

    with open(
        label_path,
        "r",
        encoding="utf-8"
    ) as f:
        label_data = json.load(f)

    label2id = label_data["label2id"]

    # JSON converts dictionary keys to strings.
    # Transformers expects integer IDs.
    id2label = {
        int(k): v
        for k, v in label_data["id2label"].items()
    }

    num_labels = len(label2id)

    # --------------------------------------------------------
    # Validate mapping
    # --------------------------------------------------------

    expected_ids = set(range(num_labels))
    actual_ids = set(id2label.keys())

    if actual_ids != expected_ids:
        raise ValueError(
            "Invalid label mapping.\n"
            f"Expected IDs: {sorted(expected_ids)}\n"
            f"Actual IDs: {sorted(actual_ids)}"
        )

    if len(id2label) != len(label2id):
        raise ValueError(
            "label2id and id2label contain different numbers "
            "of labels."
        )

    print("=" * 60)
    print("LABEL MAPPING")
    print("=" * 60)
    print(f"Number of labels: {num_labels}")

    for idx in range(min(10, num_labels)):
        print(f"{idx}: {id2label[idx]}")

    if num_labels > 10:
        print("...")

    print("=" * 60)

    return label2id, id2label, num_labels


# ============================================================
# LOAD DATA
# ============================================================

def load_data():
    train_path = os.path.join(
        DATA_DIR,
        "train.csv"
    )

    val_path = os.path.join(
        DATA_DIR,
        "val.csv"
    )

    train_df = pd.read_csv(train_path)
    val_df = pd.read_csv(val_path)

    # --------------------------------------------------------
    # Validate required columns
    # --------------------------------------------------------

    required_columns = {
        TEXT_COL,
        LABEL_COL,
        "label_id",
    }

    for column in required_columns:
        if column not in train_df.columns:
            raise ValueError(
                f"Missing required column '{column}' "
                f"in training data."
            )

        if column not in val_df.columns:
            raise ValueError(
                f"Missing required column '{column}' "
                f"in validation data."
            )

    # --------------------------------------------------------
    # Clean text
    # --------------------------------------------------------

    train_df[TEXT_COL] = (
        train_df[TEXT_COL]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    val_df[TEXT_COL] = (
        val_df[TEXT_COL]
        .fillna("")
        .astype(str)
        .str.strip()
    )

    train_df = train_df[
        train_df[TEXT_COL] != ""
    ].copy()

    val_df = val_df[
        val_df[TEXT_COL] != ""
    ].copy()

    # --------------------------------------------------------
    # Make sure labels are integers
    # --------------------------------------------------------

    train_df["label_id"] = train_df["label_id"].astype(int)
    val_df["label_id"] = val_df["label_id"].astype(int)

    # --------------------------------------------------------
    # Quick mode
    # --------------------------------------------------------

    if QUICK_MODE:

        train_df = train_df.head(
            QUICK_TRAIN_ROWS
        ).copy()

        val_df = val_df.head(
            QUICK_VAL_ROWS
        ).copy()

        print(
            f"QUICK_MODE ON: "
            f"{len(train_df)} train / "
            f"{len(val_df)} val rows, "
            f"{QUICK_EPOCHS} epoch."
        )

    else:

        print(
            f"FULL_MODE ON: "
            f"{len(train_df)} train / "
            f"{len(val_df)} val rows, "
            f"{FULL_EPOCHS} epochs."
        )

    # --------------------------------------------------------
    # Keep only the columns needed by Hugging Face Dataset
    # --------------------------------------------------------

    train_df = train_df[
        [TEXT_COL, "label_id"]
    ]

    val_df = val_df[
        [TEXT_COL, "label_id"]
    ]

    return train_df, val_df


# ============================================================
# TOKENIZATION
# ============================================================

def tokenize_datasets(train_df, val_df):

    tokenizer = AutoTokenizer.from_pretrained(
        MODEL_NAME
    )

    train_dataset = Dataset.from_pandas(
        train_df,
        preserve_index=False
    )

    val_dataset = Dataset.from_pandas(
        val_df,
        preserve_index=False
    )

    def tokenize(batch):

        return tokenizer(
            batch[TEXT_COL],
            truncation=True,
            max_length=512,
        )

    train_dataset = train_dataset.map(
        tokenize,
        batched=True,
        desc="Tokenizing training data",
    )

    val_dataset = val_dataset.map(
        tokenize,
        batched=True,
        desc="Tokenizing validation data",
    )

    # Trainer expects the target column to be called "labels".
    train_dataset = train_dataset.rename_column(
        "label_id",
        "labels"
    )

    val_dataset = val_dataset.rename_column(
        "label_id",
        "labels"
    )

    return tokenizer, train_dataset, val_dataset


# ============================================================
# METRICS
# ============================================================

def compute_metrics(eval_prediction):

    predictions, labels = eval_prediction

    # Some Transformers versions return
    # predictions as a tuple.
    if isinstance(predictions, tuple):
        predictions = predictions[0]

    predicted_labels = np.argmax(
        predictions,
        axis=-1
    )

    accuracy = accuracy_score(
        labels,
        predicted_labels
    )

    precision, recall, f1, _ = (
        precision_recall_fscore_support(
            labels,
            predicted_labels,
            average="weighted",
            zero_division=0,
        )
    )

    return {
        "accuracy": accuracy,
        "precision_weighted": precision,
        "recall_weighted": recall,
        "f1_weighted": f1,
    }


# ============================================================
# MAIN TRAINING
# ============================================================

def main():

    print("\n")
    print("=" * 60)
    print("LEGAL-BERT CLAUSE CLASSIFIER TRAINING")
    print("=" * 60)

    # --------------------------------------------------------
    # Labels
    # --------------------------------------------------------

    label2id, id2label, num_labels = (
        load_label_mapping()
    )

    if num_labels != 41:
        raise ValueError(
            f"Expected 41 CUAD classes, "
            f"but found {num_labels}."
        )

    # --------------------------------------------------------
    # Data
    # --------------------------------------------------------

    train_df, val_df = load_data()

    print("\nTraining rows:", len(train_df))
    print("Validation rows:", len(val_df))

    # --------------------------------------------------------
    # Check labels
    # --------------------------------------------------------

    invalid_train_labels = set(
        train_df["label_id"]
    ) - set(range(num_labels))

    invalid_val_labels = set(
        val_df["label_id"]
    ) - set(range(num_labels))

    if invalid_train_labels:
        raise ValueError(
            f"Invalid training labels: "
            f"{invalid_train_labels}"
        )

    if invalid_val_labels:
        raise ValueError(
            f"Invalid validation labels: "
            f"{invalid_val_labels}"
        )

    # --------------------------------------------------------
    # Tokenizer + datasets
    # --------------------------------------------------------

    tokenizer, train_dataset, val_dataset = (
        tokenize_datasets(
            train_df,
            val_df
        )
    )

    # --------------------------------------------------------
    # Model
    # --------------------------------------------------------

    print("\nLoading Legal-BERT model...")

    model = (
        AutoModelForSequenceClassification
        .from_pretrained(
            MODEL_NAME,

            num_labels=num_labels,

            id2label=id2label,

            label2id=label2id,
        )
    )

    print(
        f"Model configured for "
        f"{num_labels} clause categories."
    )

    # --------------------------------------------------------
    # Data collator
    # --------------------------------------------------------

    data_collator = DataCollatorWithPadding(
        tokenizer=tokenizer
    )

    # --------------------------------------------------------
    # Training configuration
    # --------------------------------------------------------

    if QUICK_MODE:

        epochs = QUICK_EPOCHS

        output_dir = os.path.join(
            OUT_DIR,
            "quick_training"
        )

    else:

        epochs = FULL_EPOCHS

        output_dir = OUT_DIR

    os.makedirs(
        output_dir,
        exist_ok=True
    )

    training_args = TrainingArguments(

        output_dir=output_dir,

        num_train_epochs=epochs,

        learning_rate=2e-5,

        per_device_train_batch_size=8,

        per_device_eval_batch_size=8,

        weight_decay=0.01,

        eval_strategy="epoch",

        save_strategy="epoch",

        logging_strategy="steps",

        logging_steps=25,

        load_best_model_at_end=True,

        metric_for_best_model="f1_weighted",

        greater_is_better=True,

        save_total_limit=2,

        report_to="none",

        # CPU machine
        dataloader_pin_memory=False,

        fp16=False,

        remove_unused_columns=True,
    )

    # --------------------------------------------------------
    # Trainer
    # --------------------------------------------------------

    trainer = Trainer(

        model=model,

        args=training_args,

        train_dataset=train_dataset,

        eval_dataset=val_dataset,

        processing_class=tokenizer,

        data_collator=data_collator,

        compute_metrics=compute_metrics,
    )

    # --------------------------------------------------------
    # Training
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("STARTING TRAINING")
    print("=" * 60)

    trainer.train()

    # --------------------------------------------------------
    # Final evaluation
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("VALIDATION RESULTS")
    print("=" * 60)

    metrics = trainer.evaluate()

    for key, value in metrics.items():

        if isinstance(value, float):

            print(
                f"{key}: {value:.4f}"
            )

        else:

            print(
                f"{key}: {value}"
            )

    # --------------------------------------------------------
    # Save final model
    # --------------------------------------------------------

    print("\n")
    print("=" * 60)
    print("SAVING MODEL")
    print("=" * 60)

    if QUICK_MODE:

        final_output_dir = os.path.join(
            OUT_DIR,
            "quick_model"
        )

    else:

        final_output_dir = OUT_DIR

    os.makedirs(
        final_output_dir,
        exist_ok=True
    )

    trainer.save_model(
        final_output_dir
    )

    tokenizer.save_pretrained(
        final_output_dir
    )

    # Save metrics
    metrics_path = os.path.join(
        final_output_dir,
        "training_metrics.json"
    )

    with open(
        metrics_path,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                key: (
                    float(value)
                    if isinstance(value, (np.floating, np.integer))
                    else value
                )
                for key, value in metrics.items()
            },
            f,
            indent=2,
        )

    # Save mapping alongside model
    with open(
        os.path.join(
            final_output_dir,
            "label_map.json"
        ),
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            {
                "label2id": label2id,
                "id2label": {
                    str(k): v
                    for k, v in id2label.items()
                },
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print(
        f"\nModel saved to:\n"
        f"{final_output_dir}"
    )

    print("\nTraining complete.")


# ============================================================
# ENTRY POINT
# ============================================================

if __name__ == "__main__":
    main()