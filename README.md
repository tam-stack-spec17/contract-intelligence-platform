# contract-intelligence-platform
# AI-Powered Contract Intelligence & Risk Scoring

## Project Overview

The AI-Powered Contract Intelligence & Risk Scoring project is designed to analyze legal contracts using Natural Language Processing (NLP) and Machine Learning techniques.

The system aims to automatically process contract documents, identify and classify important legal clauses, and provide structured information that can be used by downstream components for contract analysis and risk scoring.

The overall machine-learning workflow can be represented as:

Contract Document
        |
        v
Data Extraction
        |
        v
Data Cleaning & Preprocessing
        |
        v
Clause Extraction / Segmentation
        |
        v
Legal Clause Classification
        |
        v
Risk Analysis & Scoring
        |
        v
Contract Intelligence Output


# Model Training & Evaluation

## Role

**Model Training and Evaluation**

My primary responsibility in the project was to develop, fine-tune, save, and evaluate the transformer-based machine-learning model responsible for legal clause classification.

The objective of this component was to develop a model capable of taking an individual legal contract clause as input and predicting the corresponding legal clause category.

The trained classifier acts as the machine-learning layer between the processed contract clauses and the downstream contract intelligence and risk-scoring components.


# 1. Objective of the Model

Legal contracts contain many different types of clauses.

Examples include:

- Confidentiality
- Termination
- Assignment
- Indemnification
- Insurance
- Governing Law
- Liability
- Payment
- Intellectual Property
- Renewal
- Non-Compete
- Other contractual provisions

A simple keyword-based system can identify some clauses, but legal language is highly contextual.

For example, the following two clauses may express a similar legal concept:

"Either party may terminate this agreement upon thirty days' written notice."

and

"This Agreement may be ended by either party by providing written notice thirty days prior to termination."

A keyword-based system may not understand that both clauses represent the same contractual concept.

A transformer-based language model can capture contextual relationships between words and sentences.

Therefore, a transformer model specialized for legal language was selected for the clause-classification task.


# 2. Dataset

The project uses the CUAD (Contract Understanding Atticus Dataset) for legal contract clause classification.

The dataset contains contract clauses together with their corresponding clause categories.

The raw CUAD data was converted and prepared into a classification-oriented dataset before being supplied to the transformer model.

The dataset flow used by the project is:

CUAD Raw Dataset
        |
        v
Data Cleaning
        |
        v
Data Preprocessing
        |
        v
Label Encoding
        |
        v
Train / Validation / Test Split
        |
        v
Legal-BERT Training


## Processed Dataset Structure

The processed dataset is organized as:

data/
|
+-- raw/
|   |
|   +-- CUADv1.json
|   +-- test.json
|   +-- train_separate_questions.json
|   +-- cuad_train.csv
|
+-- processed/
    |
    +-- train.csv
    +-- val.csv
    +-- test.csv
    +-- label_map.json


## Purpose of Processed Files

### train.csv

Contains the training examples used to fine-tune the Legal-BERT model.

### val.csv

Contains validation examples used during training to monitor model performance.

### test.csv

Contains previously unseen examples used for final model evaluation.

### label_map.json

Stores the mapping between human-readable legal clause labels and numerical class IDs.

For example:

Confidentiality -> 0
Termination     -> 1
Assignment      -> 2
Indemnification -> 3

The actual mapping is determined from the dataset and stored in `label_map.json`.


# 3. Data Preparation

The classification model requires the legal clause text and its corresponding numerical class label.

The important fields used by the classification pipeline are:

- `clause`
- `label`
- `label_id`

The `clause` field contains the actual legal text.

The `label` field contains the human-readable legal clause category.

The `label_id` field represents the category as a numerical value that can be consumed by the classification model.


# 4. Train, Validation and Test Split

The prepared dataset is divided into three subsets:

- Training dataset
- Validation dataset
- Test dataset

The training dataset is used to fine-tune the model.

The validation dataset is used during training to monitor model performance and select the best-performing checkpoint.

The test dataset is kept separate from the training process and is used for final evaluation.

A stratified split is used to preserve the distribution of clause categories across the datasets.

The approximate split is:

Training     -> 80%
Validation   -> 10%
Testing      -> 10%

The exact number of samples depends on the cleaned dataset produced by the preprocessing pipeline.


# 5. Model Selection

The selected transformer model is:

`nlpaueb/legal-bert-base-uncased`

The model is commonly referred to as Legal-BERT.

Legal-BERT was selected because the project deals specifically with legal documents and legal language.

A general-purpose language model learns language representations from broad text sources.

A legal-domain pretrained model provides a more suitable starting point for understanding legal terminology and contractual language.

Instead of training a transformer from scratch, the pretrained Legal-BERT model is fine-tuned for the specific clause-classification task.


# 6. Model Architecture

The classification pipeline follows:

Legal Clause
     |
     v
Legal-BERT Tokenizer
     |
     v
Token IDs + Attention Mask
     |
     v
Legal-BERT
     |
     v
Classification Layer
     |
     v
Predicted Clause Category


The model was loaded using:

`AutoModelForSequenceClassification`

This adds a classification layer on top of the pretrained Legal-BERT representation.

The number of output classes is determined from the available legal clause labels.


# 7. Tokenization

Transformers cannot directly process raw text.

Therefore, each legal clause is converted into tokens using the Legal-BERT tokenizer.

The tokenization process converts:

Raw Legal Clause
        |
        v
Tokens
        |
        v
Token IDs
        |
        v
Attention Mask
        |
        v
Legal-BERT


The tokenizer was configured with:

- Truncation enabled
- Maximum sequence length of 512 tokens

The implementation uses:

```python
tokenizer(
    batch["text"],
    truncation=True,
    max_length=512
)
