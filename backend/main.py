from pathlib import Path
from typing import List, Dict, Any
import io
import re

import fitz
import torch
import pytesseract

from PIL import Image
from docx import Document
from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from transformers import (
    AutoTokenizer,
    AutoModelForSequenceClassification,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

MODEL_PATH = (
    BASE_DIR
    / "models"
    / "clause_classifier_final"
)

TESSERACT_PATH = (
    r"C:\Program Files\Tesseract-OCR\tesseract.exe"
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

MAX_FILE_SIZE = 50 * 1024 * 1024

MAX_CLAUSE_SEGMENTS = 300

CLASSIFICATION_BATCH_SIZE = 8

MIN_CLAUSE_CONFIDENCE = 0.55

MIN_CONTRACT_SIGNALS = 2


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Contract Intelligence API",
    description="AI-powered contract analysis using Legal-BERT",
    version="2.3.0",
)


# ============================================================
# CORS
# ============================================================

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:5174",
        "http://127.0.0.1:5174",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# MODEL
# ============================================================

tokenizer = None
model = None


def load_model():
    global tokenizer, model

    if not MODEL_PATH.exists():
        raise FileNotFoundError(
            f"Legal-BERT model not found at: {MODEL_PATH}"
        )

    print(
        f"[MODEL] Loading Legal-BERT from: "
        f"{MODEL_PATH}"
    )

    tokenizer = AutoTokenizer.from_pretrained(
        str(MODEL_PATH)
    )

    model = AutoModelForSequenceClassification.from_pretrained(
        str(MODEL_PATH)
    )

    model.eval()

    print("[MODEL] Loaded successfully.")

    print(
        f"[MODEL] Number of classes: "
        f"{model.config.num_labels}"
    )


load_model()


# ============================================================
# TEXT CLEANING
# ============================================================

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace("\x00", " ")

    text = re.sub(
        r"[ \t]+",
        " ",
        text,
    )

    text = re.sub(
        r"\n{3,}",
        "\n\n",
        text,
    )

    return text.strip()


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf_text(
    file_bytes: bytes,
) -> tuple[str, bool]:

    extracted_pages = []

    ocr_used = False

    try:
        pdf = fitz.open(
            stream=file_bytes,
            filetype="pdf",
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read PDF: {exc}",
        )

    for page in pdf:
        text = page.get_text("text")

        if text and text.strip():
            extracted_pages.append(text)
            continue

        # OCR fallback for image/scanned pages
        try:
            pix = page.get_pixmap(
                matrix=fitz.Matrix(2, 2),
                alpha=False,
            )

            image = Image.open(
                io.BytesIO(pix.tobytes("png"))
            )

            ocr_text = pytesseract.image_to_string(
                image
            )

            extracted_pages.append(
                ocr_text or ""
            )

            ocr_used = True

        except Exception:
            extracted_pages.append("")

    pdf.close()

    text = "\n".join(extracted_pages)

    return clean_text(text), ocr_used


# ============================================================
# DOCX EXTRACTION
# ============================================================

def extract_docx_text(
    file_bytes: bytes,
) -> str:

    try:
        document = Document(
            io.BytesIO(file_bytes)
        )
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail=f"Unable to read DOCX: {exc}",
        )

    parts = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text)

    for table in document.tables:

        for row in table.rows:

            cells = []

            for cell in row.cells:
                if cell.text.strip():
                    cells.append(
                        cell.text.strip()
                    )

            if cells:
                parts.append(
                    " | ".join(cells)
                )

    return clean_text(
        "\n".join(parts)
    )


# ============================================================
# DOCUMENT EXTRACTION
# ============================================================

def extract_document(
    filename: str,
    file_bytes: bytes,
) -> tuple[str, bool]:

    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":

        return extract_pdf_text(
            file_bytes
        )

    if suffix == ".docx":

        return (
            extract_docx_text(file_bytes),
            False,
        )

    raise HTTPException(
        status_code=400,
        detail="Only PDF and DOCX files are supported.",
    )


# ============================================================
# CONTRACT DETECTION
# ============================================================

CONTRACT_SIGNAL_PATTERNS = {
    "agreement": [
        r"\bagreement\b",
        r"\bcontract\b",
    ],
    "confidentiality": [
        r"\bconfidential\b",
        r"\bnon[- ]disclosure\b",
    ],
    "governing_law": [
        r"\bgoverning law\b",
        r"\blaws of\b",
    ],
    "intellectual_property": [
        r"\bintellectual property\b",
        r"\bpatent\b",
        r"\bcopyright\b",
        r"\btrademark\b",
    ],
    "legal_obligation": [
        r"\bshall\b",
        r"\bhereby\b",
        r"\bparty\b",
        r"\bparties\b",
    ],
    "liability": [
        r"\bliability\b",
        r"\bindemnif",
        r"\bdamages\b",
    ],
    "payment": [
        r"\bpayment\b",
        r"\bprice\b",
        r"\binvoice\b",
        r"\bpurchase\b",
    ],
    "termination": [
        r"\btermination\b",
        r"\bterminate\b",
        r"\bexpiration\b",
    ],
}


def detect_contract(
    text: str,
) -> Dict[str, Any]:

    lower_text = text.lower()

    signals = []

    for signal_name, patterns in (
        CONTRACT_SIGNAL_PATTERNS.items()
    ):

        for pattern in patterns:

            if re.search(
                pattern,
                lower_text,
            ):
                signals.append(
                    signal_name
                )
                break

    signals = list(
        dict.fromkeys(signals)
    )

    confidence = min(
        1.0,
        len(signals) / 5,
    )

    is_contract = (
        len(signals)
        >= MIN_CONTRACT_SIGNALS
    )

    return {
        "is_contract": is_contract,
        "confidence": round(
            confidence,
            2,
        ),
        "signals": signals,
    }


# ============================================================
# TEXT SEGMENTATION
# ============================================================

def segment_text(
    text: str,
) -> List[str]:

    text = clean_text(text)

    if not text:
        return []

    # Prefer paragraph/section boundaries.
    chunks = re.split(
        r"\n\s*\n+",
        text,
    )

    segments = []

    for chunk in chunks:

        chunk = clean_text(chunk)

        if len(chunk) < 80:
            continue

        # Split very large sections.
        if len(chunk) > 3500:

            sentences = re.split(
                r"(?<=[.!?])\s+",
                chunk,
            )

            current = ""

            for sentence in sentences:

                if (
                    len(current)
                    + len(sentence)
                    > 2500
                ):

                    if len(current) >= 80:
                        segments.append(
                            current.strip()
                        )

                    current = sentence

                else:

                    current += (
                        " "
                        + sentence
                    )

            if len(current.strip()) >= 80:
                segments.append(
                    current.strip()
                )

        else:

            segments.append(chunk)

    return segments[:MAX_CLAUSE_SEGMENTS]


# ============================================================
# CLAUSE RELEVANCE FILTER
# ============================================================

CLAUSE_KEYWORDS = [
    "agreement",
    "party",
    "parties",
    "term",
    "termination",
    "confidential",
    "confidentiality",
    "liability",
    "indemn",
    "warranty",
    "warranties",
    "payment",
    "purchase",
    "assignment",
    "insurance",
    "license",
    "licence",
    "intellectual property",
    "copyright",
    "patent",
    "trademark",
    "exclusive",
    "exclusivity",
    "renew",
    "renewal",
    "governing law",
    "jurisdiction",
    "dispute",
    "damages",
    "obligation",
    "shall",
    "hereby",
]


def is_relevant_clause(
    text: str,
) -> bool:

    lower = text.lower()

    keyword_hits = sum(
        1
        for keyword in CLAUSE_KEYWORDS
        if keyword in lower
    )

    return keyword_hits >= 1


# ============================================================
# MODEL LABELS
# ============================================================

DEFAULT_LABEL_NAMES = [
    "Accounting",
    "Agreement",
    "Anti-Assignment",
    "Cap On Liability",
    "Change Of Control",
    "Covenant Not To Sue",
    "Dispute Resolution",
    "Effective Date",
    "Exclusivity",
    "Expiration Date",
    "Governing Law",
    "Insurance",
    "Ip Ownership Assignment",
    "License Grant",
    "Minimum Commitment",
    "Most Favored Nation",
    "No-Solicit Of Customers",
    "No-Solicit Of Employees",
    "Non-Compete",
    "Non-Disparagement",
    "Notice",
    "Parties",
    "Payment Terms",
    "Post-Termination Services",
    "Price Restrictions",
    "Rofr/Rofo/Rofn",
    "Revenue/Profit Sharing",
    "Source Code Escrow",
    "Term",
    "Termination For Convenience",
    "Termination For Cause",
    "Third Party Beneficiary",
    "Uncapped Liability",
    "Unlimited Liability",
    "Warranty Assignment",
    "Warranty Duration",
    "Volume Restriction",
    "Audit Rights",
    "Confidentiality",
    "Data Protection",
    "Force Majeure",
]


def get_label_name(
    class_id: int,
) -> str:

    if (
        0 <= class_id
        < len(DEFAULT_LABEL_NAMES)
    ):
        return DEFAULT_LABEL_NAMES[
            class_id
        ]

    return f"Class {class_id}"


# ============================================================
# RISK WEIGHTS
# ============================================================

RISK_WEIGHTS = {
    "Uncapped Liability": 95,
    "Unlimited Liability": 95,
    "Competitive Restriction Exception": 80,
    "Ip Ownership Assignment": 70,
    "Cap On Liability": 70,
    "Exclusivity": 65,
    "Minimum Commitment": 60,
    "Anti-Assignment": 50,
    "Non-Compete": 75,
    "Termination For Cause": 55,
    "Termination For Convenience": 55,
    "Insurance": 30,
    "Warranty Duration": 30,
    "Covenant Not To Sue": 30,
    "Post-Termination Services": 35,
    "Rofr/Rofo/Rofn": 35,
    "Confidentiality": 25,
    "Governing Law": 20,
    "Payment Terms": 25,
    "Term": 20,
    "Effective Date": 10,
    "Parties": 10,
}


def calculate_risk(
    clauses: List[Dict[str, Any]],
) -> tuple[float, str, List[Dict[str, Any]]]:

    findings = []

    contributions = []

    for clause in clauses:

        label = clause["label"]

        confidence = float(
            clause["confidence"]
        )

        weight = RISK_WEIGHTS.get(
            label,
            20,
        )

        contribution = (
            confidence * weight
        )

        contributions.append(
            contribution
        )

        if contribution >= 15:

            if contribution >= 45:
                severity = "HIGH"

            elif contribution >= 25:
                severity = "MEDIUM"

            else:
                severity = "LOW"

            findings.append(
                {
                    "clause": label,
                    "severity": severity,
                    "confidence": round(
                        confidence,
                        4,
                    ),
                    "risk_weight": weight,
                    "risk_contribution": round(
                        contribution,
                        2,
                    ),
                    "evidence": clause[
                        "text"
                    ][:900],
                    "explanation": (
                        f"The model identified a "
                        f"{label} clause with "
                        f"{confidence * 100:.1f}% "
                        f"confidence. The configured "
                        f"policy risk weight is "
                        f"{weight}."
                    ),
                }
            )

    if not contributions:
        return 0.0, "LOW", findings

    # Normalize to a practical 0-100 application score.
    raw_score = (
        sum(contributions)
        / max(
            len(contributions),
            1,
        )
    )

    risk_score = min(
        100.0,
        raw_score,
    )

    if risk_score >= 70:
        risk_level = "HIGH"

    elif risk_score >= 45:
        risk_level = "MEDIUM"

    else:
        risk_level = "LOW"

    findings.sort(
        key=lambda item: item[
            "risk_contribution"
        ],
        reverse=True,
    )

    return (
        round(risk_score, 1),
        risk_level,
        findings,
    )


# ============================================================
# ENTITY EXTRACTION
# ============================================================

def extract_entities(
    text: str,
) -> List[Dict[str, str]]:

    entities = []

    # Dates
    date_patterns = [
        r"\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b",
        r"\b(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{1,2},?\s+\d{4}\b",
        r"\b\d{1,2}\s+(?:January|February|March|April|May|June|July|August|September|October|November|December)\s+\d{4}\b",
    ]

    for pattern in date_patterns:

        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):

            entities.append(
                {
                    "type": "DATE",
                    "text": match.group(0),
                }
            )

    # Monetary values
    money_pattern = (
        r"(?:US\$|\$|USD)\s?"
        r"\d[\d,]*(?:\.\d{1,2})?"
        r"(?:\s*(?:million|billion|thousand))?"
    )

    for match in re.finditer(
        money_pattern,
        text,
        re.IGNORECASE,
    ):

        entities.append(
            {
                "type": "MONEY",
                "text": match.group(0),
            }
        )

    # Jurisdiction
    jurisdiction_patterns = [
        r"laws of the\s+([A-Za-z .]+?)(?:\.|,|;|\n)",
        r"laws of\s+([A-Za-z .]+?)(?:\.|,|;|\n)",
        r"governed by the laws of\s+([A-Za-z .]+?)(?:\.|,|;|\n)",
    ]

    for pattern in jurisdiction_patterns:

        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):

            value = match.group(0).strip()

            if len(value) <= 150:

                entities.append(
                    {
                        "type": "JURISDICTION",
                        "text": value,
                    }
                )

    # Common company/party declarations.
    party_patterns = [
        r"between\s+(.{3,100}?)\s+and\s+(.{3,100}?)(?:\s+this|\s+dated|\.)",
        r"([A-Z][A-Za-z0-9&,.\- ]{2,80}(?:Corp\.|Corporation|Company|LLC|Ltd\.|Inc\.))",
    ]

    for pattern in party_patterns:

        for match in re.finditer(
            pattern,
            text,
            re.IGNORECASE,
        ):

            if match.lastindex == 2:

                for group_index in range(
                    1,
                    3,
                ):

                    value = (
                        match.group(
                            group_index
                        )
                        .strip()
                    )

                    if (
                        3
                        <= len(value)
                        <= 100
                    ):

                        entities.append(
                            {
                                "type": "PARTY",
                                "text": value,
                            }
                        )

            else:

                value = (
                    match.group(1)
                    .strip()
                )

                entities.append(
                    {
                        "type": "PARTY",
                        "text": value,
                    }
                )

    # Remove duplicates.
    unique_entities = []

    seen = set()

    for entity in entities:

        key = (
            entity["type"],
            entity["text"].lower(),
        )

        if key in seen:
            continue

        seen.add(key)

        unique_entities.append(
            entity
        )

    return unique_entities[:100]


# ============================================================
# CLAUSE CLASSIFICATION
# ============================================================

def classify_clauses(
    segments: List[str],
) -> List[Dict[str, Any]]:

    if not segments:
        return []

    relevant_segments = [
        segment
        for segment in segments
        if is_relevant_clause(segment)
    ]

    if not relevant_segments:
        relevant_segments = segments[:20]

    results = []

    for start in range(
        0,
        len(relevant_segments),
        CLASSIFICATION_BATCH_SIZE,
    ):

        batch = relevant_segments[
            start:
            start
            + CLASSIFICATION_BATCH_SIZE
        ]

        encoded = tokenizer(
            batch,
            padding=True,
            truncation=True,
            max_length=512,
            return_tensors="pt",
        )

        with torch.no_grad():

            outputs = model(
                **encoded
            )

        probabilities = torch.softmax(
            outputs.logits,
            dim=-1,
        )

        confidences, class_ids = torch.max(
            probabilities,
            dim=-1,
        )

        for text, confidence, class_id in zip(
            batch,
            confidences.tolist(),
            class_ids.tolist(),
        ):

            if (
                confidence
                < MIN_CLAUSE_CONFIDENCE
            ):
                continue

            label = get_label_name(
                class_id
            )

            results.append(
                {
                    "label": label,
                    "confidence": round(
                        confidence,
                        4,
                    ),
                    "class_id": int(
                        class_id
                    ),
                    "text": text[:3000],
                }
            )

    return results


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():

    return {
        "status": "ok",
        "service": "contract-intelligence-api",
        "model_loaded": model is not None,
        "model_classes": (
            model.config.num_labels
            if model is not None
            else 0
        ),
        "ocr_available": Path(
            TESSERACT_PATH
        ).exists(),
    }


# ============================================================
# CONTRACT ANALYSIS
# ============================================================

@app.post("/api/contracts/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
):

    filename = file.filename or ""

    suffix = Path(
        filename
    ).suffix.lower()

    if suffix not in [
        ".pdf",
        ".docx",
    ]:

        raise HTTPException(
            status_code=400,
            detail=(
                "Only PDF and DOCX files "
                "are supported."
            ),
        )

    file_bytes = await file.read()

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    if len(file_bytes) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail=(
                "The uploaded file exceeds "
                "the 50 MB limit."
            ),
        )

    text, ocr_used = extract_document(
        filename,
        file_bytes,
    )

    if len(text) < 50:

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Unable to extract enough "
                    "text from the uploaded document."
                ),
                "document_type": "unreadable",
                "ocr_used": ocr_used,
            },
        )

    contract_detection = detect_contract(
        text
    )

    if not contract_detection[
        "is_contract"
    ]:

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "The uploaded document does "
                    "not appear to contain enough "
                    "contractual language for "
                    "reliable analysis."
                ),
                "document_type": "non_contract",
                "contract_confidence": (
                    contract_detection[
                        "confidence"
                    ]
                ),
                "signals": (
                    contract_detection[
                        "signals"
                    ]
                ),
            },
        )

    segments = segment_text(
        text
    )

    clauses = classify_clauses(
        segments
    )

    entities = extract_entities(
        text
    )

    risk_score, risk_level, findings = (
        calculate_risk(clauses)
    )

    # Convert clauses to frontend-friendly objects.
    frontend_clauses = []

    for clause in clauses:

        weight = RISK_WEIGHTS.get(
            clause["label"],
            20,
        )

        contribution = (
            clause["confidence"]
            * weight
        )

        if contribution >= 45:
            status = "High Risk"

        elif contribution >= 25:
            status = "Medium Risk"

        else:
            status = "Low Risk"

        frontend_clauses.append(
            {
                "name": clause["label"],
                "confidence": clause[
                    "confidence"
                ],
                "class_id": clause[
                    "class_id"
                ],
                "text": clause["text"],
                "status": status,
                "description": (
                    "Clause detected by the "
                    "Legal-BERT classifier."
                ),
            }
        )

    return {
        "contract_name": filename,

        "risk_score": risk_score,

        "risk_level": risk_level,

        "entities": entities,

        "clauses": frontend_clauses,

        "findings": findings,

        "metadata": {
            "file_type": suffix,
            "file_size_bytes": len(
                file_bytes
            ),
            "text_characters": len(
                text
            ),
            "segments_analyzed": len(
                segments
            ),
            "clauses_returned": len(
                frontend_clauses
            ),
            "ocr_used": ocr_used,
            "model_classes": (
                model.config.num_labels
                if model is not None
                else 0
            ),
            "contract_detection": (
                contract_detection
            ),
            "minimum_clause_confidence": (
                MIN_CLAUSE_CONFIDENCE
            ),
        },

        "disclaimer": (
            "Risk scores are application-level "
            "policy indicators generated from "
            "model predictions and configured "
            "risk weights. They are not legal advice."
        ),
    }