"""
Step 6: Evaluate the fine-tuned classifier + post-processing heuristics.
Week 2, Day 5-7.
"""

import json
import os

import matplotlib.pyplot as plt
import numpy as np
import pandas as pd
import torch
from sklearn.metrics import classification_report, confusion_matrix
from transformers import AutoModelForSequenceClassification, AutoTokenizer

MODEL_DIR = "models/clause_classifier"
DATA_DIR = "data/processed"
OUT_DIR = "reports"
TEXT_COL = "clause"  # confirmed CUAD classification dataset column


def main():
    os.makedirs(OUT_DIR, exist_ok=True)

    with open(f"{DATA_DIR}/label_map.json") as f:
        label_map = json.load(f)
    id2label = {int(k): v for k, v in label_map["id2label"].items()}

    tokenizer = AutoTokenizer.from_pretrained(MODEL_DIR)
    model = AutoModelForSequenceClassification.from_pretrained(MODEL_DIR)
    model.eval()

    df = pd.read_csv(f"{DATA_DIR}/test.csv")
    text_col = TEXT_COL

    all_preds, all_probs, all_labels = [], [], []

    with torch.no_grad():
        batch_size = 16
        for i in range(0, len(df), batch_size):
            batch = df.iloc[i:i + batch_size]
            enc = tokenizer(
                batch[text_col].tolist(),
                truncation=True,
                padding=True,
                max_length=512,
                return_tensors="pt",
            )
            logits = model(**enc).logits
            probs = torch.softmax(logits, dim=-1)
            preds = torch.argmax(probs, dim=-1)

            all_preds.extend(preds.tolist())
            all_probs.extend(probs.max(dim=-1).values.tolist())
            all_labels.extend(batch["label_id"].tolist())

    # --- Standard classification report ---
    target_names = [id2label[i] for i in sorted(id2label)]
    print(classification_report(all_labels, all_preds, target_names=target_names, zero_division=0))

    # --- Confusion matrix ---
    cm = confusion_matrix(all_labels, all_preds)
    plt.figure(figsize=(12, 10))
    plt.imshow(cm, cmap="Blues")
    plt.title("Confusion matrix — clause classifier")
    plt.xlabel("Predicted")
    plt.ylabel("True")
    plt.colorbar()
    plt.tight_layout()
    plt.savefig(f"{OUT_DIR}/confusion_matrix.png")
    print(f"\nSaved -> {OUT_DIR}/confusion_matrix.png")

    # --- Post-processing heuristic: confidence thresholding ---
    # Instead of trusting every raw prediction, flag low-confidence calls
    # for human review. This is the "post-processing heuristic to improve
    # confidence scores" step in the plan — it trades coverage for
    # precision on the predictions you do auto-accept.
    preds_arr = np.array(all_preds)
    labels_arr = np.array(all_labels)
    probs_arr = np.array(all_probs)

    print("\nConfidence-threshold post-processing:")
    for threshold in (0.5, 0.6, 0.7, 0.8, 0.9):
        keep = probs_arr >= threshold
        flagged_pct = 1 - keep.mean()
        acc_on_kept = (preds_arr[keep] == labels_arr[keep]).mean() if keep.sum() else float("nan")
        print(
            f"  threshold={threshold:.1f}  |  flagged for review: {flagged_pct:6.1%}  "
            f"|  accuracy on auto-accepted: {acc_on_kept:6.1%}"
        )

    # Save per-example predictions for manual error analysis
    out_df = df.copy()
    out_df["true_label"] = [id2label[l] for l in all_labels]
    out_df["pred_label"] = [id2label[p] for p in all_preds]
    out_df["confidence"] = all_probs
    out_df.to_csv(f"{OUT_DIR}/test_predictions.csv", index=False)
    print(f"\nSaved per-example predictions -> {OUT_DIR}/test_predictions.csv")


if __name__ == "__main__":
    main()
