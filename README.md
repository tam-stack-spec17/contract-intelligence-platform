# ContractIQ — Contract Intelligence Platform

ContractIQ is an end-to-end AI-powered SaaS platform for contract analysis. It transforms PDF/DOCX agreements into structured legal clauses, confidence signals, entities, and explainable risk summaries through a React frontend, FastAPI backend, Legal-BERT classifier, and SQLite persistence.

## Project status

**Final review / submission build**

Implemented:
- PDF and DOCX contract ingestion
- PDF text extraction with OCR fallback
- Contract-document validation
- Clause segmentation and relevance filtering
- Legal-BERT clause classification across 41 CUAD categories
- Confidence scoring
- Clause-level and aggregate risk scoring
- Runtime entity extraction
- Persistent Contract Library and analysis history
- JWT authentication and password recovery workflow
- React-based SaaS dashboard, Risk Center, Clause Intelligence, Entities and Settings views
- FastAPI API layer and SQLite database

Not yet implemented:
- Trained spaCy NER model
- Dedicated anomaly/unusual-language detection model
- Production deployment hardening and production email service

> **Important:** Risk scores are prototype application-level decision-support scores, not legal advice.

## Architecture

```text
PDF / DOCX
   │
   ├── Text extraction
   │      └── OCR fallback for scanned PDFs
   │
   ├── Contract validation
   │
   ├── Clause segmentation
   │
   ├── Legal-BERT classifier
   │      └── 41 CUAD legal clause categories
   │
   ├── Confidence + risk scoring
   │
   ├── Entity extraction
   │
   └── Structured JSON
          │
          ├── FastAPI
          ├── SQLite persistence
          └── React SaaS dashboard
```

## AI pipeline

1. **Ingestion** — Accept PDF/DOCX files.
2. **Extraction** — Extract native text; use OCR for scanned PDFs.
3. **Validation** — Check whether the uploaded document has contract-like signals.
4. **Segmentation** — Break long documents into reviewable clauses/segments.
5. **Classification** — Run Legal-BERT over relevant segments.
6. **Confidence** — Preserve model confidence for each prediction.
7. **Risk scoring** — Map detected clause categories to application-level risk weights and aggregate them.
8. **Entities** — Extract important person, organization, date, monetary and other contract entities.
9. **Persistence** — Store contract metadata and analysis results in SQLite.
10. **Presentation** — Expose the results through the React workspace.

## Model and evaluation

The committed evaluation artifact reports:

| Metric | Value |
|---|---:|
| Test accuracy | 0.81 |
| Weighted F1 | 0.8007 |
| Weighted precision | 0.809 |
| Weighted recall | 0.81 |
| Number of classes | 41 |

The training/evaluation basis is the CUAD contract dataset, which contains more than 500 contracts and 41 legal clause categories.

## Example analysis output

Current committed demonstration artifact:

- Total clauses: **88**
- Overall risk score: **65.41**
- Overall risk level: **MEDIUM**
- Average clause risk: **45.68**
- Maximum clause risk: **95**
- High-risk clauses: **7**
- Medium-risk clauses: **27**
- Low-risk clauses: **54**

## Technology stack

### Frontend
- React
- Vite
- CSS
- Fetch-based API integration

### Backend
- Python
- FastAPI
- Uvicorn
- SQLAlchemy
- SQLite
- JWT authentication
- Argon2 password hashing
- SMTP-ready password recovery

### AI / NLP
- Hugging Face Transformers
- Legal-BERT classifier
- PyTorch
- PyMuPDF
- Tesseract OCR
- Regex-based runtime entity extraction

## Repository structure

```text
contract-intelligence-platform/
├── backend/
│   ├── main.py
│   ├── auth.py
│   ├── database.py
│   └── models.py
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── App.css
│   │   └── services/
│   │       └── api.js
│   └── package.json
├── models/
│   └── clause_classifier_final/
├── src/
│   └── final_dashboard_output.json
├── data/
├── docs/
└── README.md
```

## Local setup

### Backend

```powershell
cd backend
python -m uvicorn main:app --host 127.0.0.1 --port 8000
```

### Frontend

```powershell
cd frontend
npm.cmd install
npm.cmd run dev
```

The backend runs at `http://127.0.0.1:8000`.

## Core API endpoints

### Authentication
- `POST /api/auth/register`
- `POST /api/auth/login`
- `GET /api/auth/me`
- `PUT /api/auth/profile`
- `POST /api/auth/change-password`
- `POST /api/auth/forgot-password`
- `POST /api/auth/verify-otp`
- `POST /api/auth/reset-password`

### Contract workspace
- `GET /api/dashboard`
- `GET /api/contracts`
- `POST /api/contracts`
- `GET /api/contracts/{id}`
- `PATCH /api/contracts/{id}`
- `DELETE /api/contracts/{id}`

## Security / configuration

Do not commit credentials.

Use a local `.env` file for SMTP settings:

```env
SMTP_HOST=smtp.gmail.com
SMTP_PORT=587
SMTP_USERNAME=your-account@gmail.com
SMTP_PASSWORD=your-google-app-password
SMTP_FROM=your-account@gmail.com
```

A production deployment should store these values in a secret manager or deployment environment.

## Review/demo flow

1. Sign in or create an account.
2. Open the Contract Library / dashboard.
3. Upload a real PDF or DOCX contract.
4. Run analysis.
5. Review detected clauses, confidence, risk and entities.
6. Open the saved contract to show persistence.
7. Demonstrate password recovery if required.

## Project boundaries

ContractIQ is a prototype decision-support platform. Model predictions and risk scores should be reviewed by qualified legal professionals before being relied upon for legal decisions.

## Final submission note

This repository represents the integrated application build for the final project review: frontend + API + AI model + persistence + authentication + documented limitations.
