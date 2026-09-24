# Project Documentation — ContractIQ

## 1. Executive summary

ContractIQ is a Contract Intelligence platform designed to reduce the effort required to review legal agreements. The system combines document ingestion, OCR/text extraction, Legal-BERT clause classification, explainable risk scoring, entity extraction, persistence and a React-based SaaS interface.

The implementation is organized around two related concepts:

- **AI pipeline:** document → text → clause → classification → confidence → risk → entities → structured output
- **System integration:** React frontend ↔ FastAPI backend ↔ Legal-BERT processing ↔ SQLite persistence

## 2. Functional workflow

### 2.1 Document ingestion
The user uploads a PDF or DOCX contract.

### 2.2 Text extraction
The backend extracts native text. For scanned PDFs, the application uses OCR as a fallback.

### 2.3 Contract validation
The backend checks the extracted content for contract-like signals before analysis.

### 2.4 Clause processing
The document is segmented into smaller text units and filtered for relevant clauses.

### 2.5 Legal-BERT classification
Relevant segments are passed to the fine-tuned Legal-BERT classifier. The committed model contains 41 output classes corresponding to the CUAD clause categories used for the project.

### 2.6 Explainable risk scoring
Each detected clause receives an application-level risk contribution. Clause risks are aggregated into an overall contract risk score and risk level.

### 2.7 Entity extraction
Important entities are extracted at runtime and surfaced with the analysis.

### 2.8 Persistence
Contracts, users and analysis results are persisted in SQLite. This allows the Contract Library to survive page refreshes and separate sessions.

### 2.9 Frontend presentation
The React frontend presents:
- Dashboard
- Contract Library
- Risk Center
- Clause Intelligence
- Entities
- Settings
- Authentication and recovery workflow

## 3. Architecture

```text
                    ┌─────────────────────┐
                    │     React UI        │
                    │ Dashboard / Library │
                    └──────────┬──────────┘
                               │ HTTP/JSON
                               ▼
                    ┌─────────────────────┐
                    │      FastAPI        │
                    │ Auth / Contracts    │
                    │ Analysis / Dashboard│
                    └───────┬─────┬───────┘
                            │     │
                   ┌────────┘     └─────────┐
                   ▼                        ▼
          ┌─────────────────┐       ┌──────────────┐
          │ AI / NLP layer  │       │   SQLite     │
          │ Legal-BERT      │       │ users        │
          │ OCR / extraction │       │ contracts    │
          │ risk / entities │       │ analyses     │
          └─────────────────┘       └──────────────┘
```

## 4. Data flow

```text
Upload
  ↓
PDF/DOCX parsing
  ↓
OCR fallback
  ↓
Contract validation
  ↓
Segmentation
  ↓
Relevant clause filtering
  ↓
Legal-BERT inference
  ↓
Confidence
  ↓
Risk scoring
  ↓
Entity extraction
  ↓
Result JSON
  ↓
SQLite
  ↓
React dashboard
```

## 5. Machine learning component

### Dataset
CUAD (Contract Understanding Atticus Dataset) was used as the project basis. The dataset contains more than 500 contracts and 41 legal clause categories.

### Evaluation
Current committed evaluation artifact:

- Test accuracy: **0.81**
- Weighted F1: **0.8007**
- Weighted precision: **0.809**
- Weighted recall: **0.81**
- Classes: **41**

### Interpretation
The classifier is strong enough for a project prototype and demonstrates useful multi-class legal clause recognition. The application should still be treated as decision support rather than an autonomous legal decision-maker.

## 6. Risk methodology

The risk layer is an application-level scoring system.

For a clause:

```text
clause risk = category risk weight × model confidence
```

The contract-level score aggregates detected clause risks and derives a risk level.

Example committed output:

```text
Total clauses         88
Overall risk score    65.41
Overall risk level    MEDIUM
Average clause risk   45.68
Maximum clause risk   95
High-risk clauses     7
Medium-risk clauses   27
Low-risk clauses      54
```

These values are prototype decision-support outputs and are not legal advice.

## 7. Authentication

The backend provides JWT-based authentication, password hashing and protected contract endpoints.

Password recovery supports:
1. Enter registered email
2. Generate one-time verification code
3. Verify the code
4. Set a new password
5. Return to login

SMTP can be configured with environment variables for production-style delivery.

## 8. Persistence model

The application stores:

### User
- id
- name
- email
- company
- password hash
- verification state
- timestamps

### Contract
- id
- user_id
- filename
- stored path
- folder
- status
- favorite
- risk score
- risk level
- timestamps

### Analysis
- id
- contract id
- serialized result JSON
- creation time

### Email OTP
- user id
- purpose
- hashed OTP
- expiry time
- attempts
- used flag

## 9. What is complete

- End-to-end contract analysis
- PDF/DOCX ingestion
- OCR fallback
- CUAD-based 41-class clause classifier
- Confidence-aware predictions
- Risk scoring
- Entity extraction
- Contract persistence
- Authentication
- Password recovery workflow
- React SaaS interface
- FastAPI integration

## 10. Known limitations / future work

The current project artifact explicitly records the following as future work:

- Train/integrate a dedicated spaCy NER model
- Add anomaly or unusual-language detection
- Calibrate risk scoring on a broader validation set
- Harden production deployment
- Use a production-grade email/secret-management setup

## 11. Review positioning

The project should be presented as an integrated prototype demonstrating:
- machine learning
- NLP
- backend API engineering
- frontend product development
- persistence
- authentication
- explainable application-level risk presentation

It should not be presented as an autonomous legal advice system.
