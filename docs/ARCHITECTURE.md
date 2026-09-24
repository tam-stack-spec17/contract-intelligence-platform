# Architecture — ContractIQ

## System overview

```text
Users
  │
  ▼
React + Vite
  │
  │ HTTP / JSON + JWT
  ▼
FastAPI
  ├── Auth
  ├── Contract CRUD
  ├── Dashboard
  ├── Upload / analysis
  └── Password recovery
        │
        ├── PDF/DOCX extraction
        ├── OCR fallback
        ├── clause segmentation
        ├── Legal-BERT inference
        ├── confidence
        ├── risk scoring
        └── entity extraction
        │
        ▼
SQLite
  ├── users
  ├── contracts
  ├── analyses
  └── email_otps
```

## Pipeline vs integration

### Pipeline
The sequence of intelligence operations:

`file → extraction/OCR → segmentation → classifier → confidence → risk → entities → JSON`

### Integration
The application-level connection:

`React → FastAPI → AI processing → SQLite → React`

Both are required to make the prototype usable as a product.
