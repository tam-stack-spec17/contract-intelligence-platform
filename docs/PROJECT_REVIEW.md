# Final Project Review — ContractIQ

## Project title

**ContractIQ — Contract Intelligence Platform**

## Review-ready summary

ContractIQ is an end-to-end AI-powered contract analysis application designed to transform unstructured agreements into structured legal intelligence.

## What was implemented

### AI / NLP
- Legal-BERT clause classification
- 41 CUAD categories
- Confidence scores
- Risk scoring
- Runtime entity extraction
- OCR fallback for scanned PDFs

### Backend
- FastAPI REST API
- JWT authentication
- Argon2 password hashing
- Contract persistence
- Analysis persistence
- Password recovery / OTP workflow

### Frontend
- React + Vite
- Dashboard
- Contract Library
- Risk Center
- Clause Intelligence
- Entities
- Settings
- Authentication screens

## End-to-end demonstration

```text
Upload contract
     ↓
Extract text / OCR
     ↓
Detect contract content
     ↓
Segment clauses
     ↓
Legal-BERT classification
     ↓
Confidence + risk scoring
     ↓
Entity extraction
     ↓
Persist result
     ↓
Display in dashboard
```

## Current model result

- Test accuracy: 0.81
- Weighted F1: 0.8007
- 41 clause classes

## Example application result

- 88 clauses
- Overall risk score: 65.41
- Overall risk level: MEDIUM
- 7 high-risk clauses
- 27 medium-risk clauses
- 54 low-risk clauses

## Limitations stated for review

- Dedicated trained NER is future work
- Dedicated anomaly detection is future work
- Risk scores are prototype decision-support indicators
- Production deployment hardening is future work

## Suggested 60-second presentation

> “We built ContractIQ as an integrated Contract Intelligence platform. A real PDF or DOCX enters through the React application and is processed by FastAPI. The backend extracts text, uses OCR when required, segments the document, and sends relevant clauses through a fine-tuned Legal-BERT classifier covering 41 CUAD categories. We preserve confidence, convert clause classifications into application-level risk signals, extract entities, persist the results in SQLite, and surface everything through a SaaS-style dashboard. The result is an end-to-end pipeline plus the integration layer required to turn the model into a usable product.”
