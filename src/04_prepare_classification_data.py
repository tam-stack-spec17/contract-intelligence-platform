"""
Step 4: Prepare train/val/test splits for clause classification.
Week 2, Day 1 (feeds into fine-tuning, Day 1-4).
"""

import json
import os

import pandas as pd
from sklearn.model_selection import train_test_split

IN_PATH = "data/raw/cuad_train.csv"
OUT_DIR = "data/processed"

# Confirmed schema: ['file_name', 'clause', 'pages', 'class_id', 'label', 'start_at', 'end_at']
TEXT_COL = "clause"
LABEL_COL = "label"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)
    df = pd.read_csv(IN_PATH)

    text_col = TEXT_COL
    label_col = LABEL_COL

    df = df.dropna(subset=[text_col, label_col]).reset_index(drop=True)
    # <omitted> markers replace irrelevant fragments within a clause (CUAD's
    # redaction convention) — drop rows that are ONLY that placeholder.
    df = df[df[text_col].str.strip() != "<omitted>"].reset_index(drop=True)

    labels = sorted(df[label_col].unique())
    label2id = {label: i for i, label in enumerate(labels)}
    id2label = {i: label for label, i in label2id.items()}
    df["label_id"] = df[label_col].map(label2id)

    # sklearn's stratified split needs >=2 examples per class in the split
    # being stratified against. Drop classes too rare for that rather than
    # crashing — with 41 classes this can bite you right when you're
    # short on time.
    counts = df[label_col].value_counts()
    too_rare = counts[counts < 4].index.tolist()
    if too_rare:
        print(f"Dropping {len(too_rare)} classes with <4 examples (can't stratify): {too_rare}")
        df = df[~df[label_col].isin(too_rare)].reset_index(drop=True)
        df["label_id"] = df[label_col].map(label2id)  # ids stay consistent with label_map.json

    # Stratified split keeps the class balance consistent across train/val/test,
    # which matters here given CUAD's per-clause class imbalance (see Step 2).
    train_df, temp_df = train_test_split(
        df, test_size=0.2, stratify=df["label_id"], random_state=42
    )
    val_df, test_df = train_test_split(
        temp_df, test_size=0.5, stratify=temp_df["label_id"], random_state=42
    )

    train_df.to_csv(f"{OUT_DIR}/train.csv", index=False)
    val_df.to_csv(f"{OUT_DIR}/val.csv", index=False)
    test_df.to_csv(f"{OUT_DIR}/test.csv", index=False)

    with open(f"{OUT_DIR}/label_map.json", "w") as f:
        json.dump({"label2id": label2id, "id2label": id2label}, f, indent=2)

    print(f"train={len(train_df)}  val={len(val_df)}  test={len(test_df)}  classes={len(labels)}")
    print(f"Saved -> {OUT_DIR}/{{train,val,test}}.csv and label_map.json")


if __name__ == "__main__":
    main()
