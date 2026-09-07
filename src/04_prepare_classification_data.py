import json
import os
import pandas as pd

from sklearn.model_selection import train_test_split


IN_PATH = "data/raw/cuad_train.csv"
OUT_DIR = "data/processed"

TEXT_COL = "clause"
LABEL_COL = "label"


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    df = pd.read_csv(IN_PATH)

    df = df.dropna(subset=[TEXT_COL, LABEL_COL]).reset_index(drop=True)

    df[TEXT_COL] = df[TEXT_COL].astype(str).str.strip()
    df[LABEL_COL] = df[LABEL_COL].astype(str).str.strip()

    df = df[df[TEXT_COL] != ""].reset_index(drop=True)

    # Remove duplicate clause/label pairs
    df = df.drop_duplicates(subset=[TEXT_COL, LABEL_COL]).reset_index(drop=True)

    print(f"Initial dataset: {len(df)} rows")
    print(f"Initial classes: {df[LABEL_COL].nunique()}")

    # Remove classes with fewer than 4 examples so that
    # stratified train/validation/test splitting is possible.
    counts = df[LABEL_COL].value_counts()

    too_rare = counts[counts < 4].index.tolist()

    if too_rare:
        print(f"Dropping {len(too_rare)} rare classes:")
        print(too_rare)

        df = df[~df[LABEL_COL].isin(too_rare)].reset_index(drop=True)

    # IMPORTANT:
    # Create label mappings AFTER rare classes have been removed.
    labels = sorted(df[LABEL_COL].unique())

    label2id = {
        label: idx
        for idx, label in enumerate(labels)
    }

    id2label = {
        idx: label
        for label, idx in label2id.items()
    }

    df["label_id"] = df[LABEL_COL].map(label2id)

    print(f"\nFinal dataset: {len(df)} rows")
    print(f"Final classes: {len(labels)}")

    print("\nClass distribution:")
    print(df[LABEL_COL].value_counts().to_string())

    # First split: 80% train, 20% temporary
    train_df, temp_df = train_test_split(
        df,
        test_size=0.20,
        stratify=df["label_id"],
        random_state=42,
    )

    # Second split: 10% validation, 10% test
    val_df, test_df = train_test_split(
        temp_df,
        test_size=0.50,
        stratify=temp_df["label_id"],
        random_state=42,
    )

    train_df.to_csv(
        f"{OUT_DIR}/train.csv",
        index=False,
    )

    val_df.to_csv(
        f"{OUT_DIR}/val.csv",
        index=False,
    )

    test_df.to_csv(
        f"{OUT_DIR}/test.csv",
        index=False,
    )

    with open(
        f"{OUT_DIR}/label_map.json",
        "w",
        encoding="utf-8",
    ) as f:
        json.dump(
            {
                "label2id": label2id,
                "id2label": id2label,
            },
            f,
            indent=2,
            ensure_ascii=False,
        )

    print("\nDataset preparation complete.")
    print(f"Train: {len(train_df)}")
    print(f"Validation: {len(val_df)}")
    print(f"Test: {len(test_df)}")
    print(f"Classes: {len(labels)}")


if __name__ == "__main__":
    main()