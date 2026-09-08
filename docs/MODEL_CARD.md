# Model Card — ContractIQ Legal-BERT Classifier

## Purpose

A fine-tuned Legal-BERT classifier is used to map relevant contract text segments to CUAD legal clause categories.

## Task

Multi-class legal clause classification.

## Number of classes

**41**

## Evaluation

| Metric | Value |
|---|---:|
| Test accuracy | 0.81 |
| Weighted F1 | 0.8007 |
| Weighted precision | 0.809 |
| Weighted recall | 0.81 |

## Dataset basis

CUAD (Contract Understanding Atticus Dataset), with more than 500 contracts and 41 legal clause categories.

## Intended use

- Contract-review assistance
- Clause discovery
- Risk triage
- Structured legal-document analytics

## Out of scope

- Independent legal advice
- Automatic legal decisions
- Guaranteed correctness on arbitrary contracts
- Replacement for qualified legal review

## Application layer

The application combines model output with:
- confidence scores
- category-level risk weights
- document context
- contract-level aggregation

The resulting risk score is an application-level prototype and should be interpreted as a prioritization signal.
