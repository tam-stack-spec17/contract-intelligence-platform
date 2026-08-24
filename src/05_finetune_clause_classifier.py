"""
Step 5: Fine-tune a transformer for legal clause classification.
Week 2, Day 1-4.

Swap MODEL_NAME to compare backbones — worth reporting more than one:
  - "nlpaueb/legal-bert-base-uncased"  pretrained on legal text (default, usually strongest)
  - "law-ai/InLegalBERT"               alternative legal-domain model
  - "roberta-base"                     general-purpose comparison point
"""

import json

import numpy as np
import pandas as pd
import evaluate
from datasets import Dataset
from transformers import (
    AutoModelForSequenceClassification,
    AutoTokenizer,
    DataCollatorWithPadding,
    Trainer,
    TrainingArguments,
)

MODEL_NAME = "nlpaueb/legal-bert-base-uncased"
DATA_DIR = "data/processed"
OUT_DIR = "models/clause_classifier"
TEXT_COL = "clause"  # confirmed CUAD classification dataset column

# --- Deadline mode -----------------------------------------------------
# Set QUICK_MODE = True to get a fast end-to-end run (subsampled data,
# fewer epochs) so you can confirm the whole pipeline works before
# committing to a full run. Flip back to False once you've verified it
# and have time for the real training run — the quick-mode numbers are
# not what you want to report.
QUICK_MODE = False
QUICK_TRAIN_ROWS = 2000
QUICK_VAL_ROWS = 400
QUICK_EPOCHS = 1
FULL_EPOCHS = 4
# -------------------------------------------------------------------------


def load_split(name, text_col, max_rows=None):
    df = pd.read_csv(f"{DATA_DIR}/{name}.csv")
    if max_rows:
        df = df.sample(n=min(max_rows, len(df)), random_state=42)
    return Dataset.from_pandas(
        df[[text_col, "label_id"]].rename(columns={text_col: "text", "label_id": "labels"})
    )


def main():
    with open(f"{DATA_DIR}/label_map.json") as f:
        label_map = json.load(f)
    id2label = {int(k): v for k, v in label_map["id2label"].items()}
    label2id = label_map["label2id"]
    num_labels = len(id2label)

    tokenizer = AutoTokenizer.from_pretrained(MODEL_NAME)

    def tokenize(batch):
        return tokenizer(batch["text"], truncation=True, max_length=512)

    if QUICK_MODE:
        print(f"QUICK_MODE on: {QUICK_TRAIN_ROWS} train / {QUICK_VAL_ROWS} val rows, "
              f"{QUICK_EPOCHS} epoch. For smoke-testing the pipeline only.")
        train_ds = load_split("train", TEXT_COL, max_rows=QUICK_TRAIN_ROWS).map(tokenize, batched=True)
        val_ds = load_split("val", TEXT_COL, max_rows=QUICK_VAL_ROWS).map(tokenize, batched=True)
    else:
        train_ds = load_split("train", TEXT_COL).map(tokenize, batched=True)
        val_ds = load_split("val", TEXT_COL).map(tokenize, batched=True)

    model = AutoModelForSequenceClassification.from_pretrained(
        MODEL_NAME, num_labels=num_labels, id2label=id2label, label2id=label2id
    )

    f1_metric = evaluate.load("f1")
    precision_metric = evaluate.load("precision")
    recall_metric = evaluate.load("recall")

    def compute_metrics(eval_pred):
        logits, labels = eval_pred
        preds = np.argmax(logits, axis=-1)
        return {
            "f1_weighted": f1_metric.compute(predictions=preds, references=labels, average="weighted")["f1"],
            "precision_weighted": precision_metric.compute(predictions=preds, references=labels, average="weighted")["precision"],
            "recall_weighted": recall_metric.compute(predictions=preds, references=labels, average="weighted")["recall"],
        }

    args = TrainingArguments(
        output_dir=OUT_DIR,
        eval_strategy="epoch",
        save_strategy="epoch",
        learning_rate=2e-5,
        per_device_train_batch_size=8,
        per_device_eval_batch_size=8,
        num_train_epochs=QUICK_EPOCHS if QUICK_MODE else FULL_EPOCHS,
        weight_decay=0.01,
        load_best_model_at_end=True,
        metric_for_best_model="f1_weighted",
        logging_steps=50,
    )

    trainer = Trainer(
        model=model,
        args=args,
        train_dataset=train_ds,
        eval_dataset=val_ds,
        data_collator=DataCollatorWithPadding(tokenizer=tokenizer),
        compute_metrics=compute_metrics,
    )

    trainer.train()
    trainer.save_model(OUT_DIR)
    tokenizer.save_pretrained(OUT_DIR)
    print(f"\nModel + tokenizer saved -> {OUT_DIR}")


if __name__ == "__main__":
    main()
