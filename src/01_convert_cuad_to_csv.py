import json
import os
import re
import pandas as pd

INPUT_PATH = "data/cuad_data/CUADv1.json"
OUTPUT_PATH = "data/raw/cuad_train.csv"


def extract_category(question):
    """
    Extract the CUAD clause category from questions such as:

    Highlight the parts ... related to "Parties" ...
    """
    match = re.search(r'related to "([^"]+)"', question)

    if match:
        return match.group(1).strip()

    return question.strip()


def main():
    os.makedirs(os.path.dirname(OUTPUT_PATH), exist_ok=True)

    with open(INPUT_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)

    rows = []

    for item in data.get("data", []):
        for paragraph in item.get("paragraphs", []):
            context = paragraph.get("context", "")

            for qa in paragraph.get("qas", []):
                question = qa.get("question", "")
                label = extract_category(question)

                for answer in qa.get("answers", []):
                    text = answer.get("text", "").strip()

                    if text:
                        rows.append(
                            {
                                "clause": text,
                                "label": label,
                                "context": context,
                            }
                        )

    df = pd.DataFrame(rows)

    df = df.dropna(subset=["clause", "label"])
    df["clause"] = df["clause"].str.strip()
    df["label"] = df["label"].str.strip()

    df = df[df["clause"] != ""]
    df = df.drop_duplicates(subset=["clause", "label"])

    print("Dataset shape:", df.shape)
    print("Unique labels:", df["label"].nunique())
    print("\nLabels:")
    print(df["label"].value_counts().to_string())

    df.to_csv(OUTPUT_PATH, index=False)

    print(f"\nSaved dataset to: {OUTPUT_PATH}")


if __name__ == "__main__":
    main()