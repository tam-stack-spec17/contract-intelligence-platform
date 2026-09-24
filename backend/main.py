from pathlib import Path
from typing import List, Dict, Any, Optional
import io
import re
import json
import shutil
import hashlib
import secrets
import os
import smtplib
import requests
from email.message import EmailMessage
from datetime import datetime, timedelta

import fitz
import pytesseract

from PIL import Image
from docx import Document

from fastapi import (
    FastAPI,
    File,
    UploadFile,
    HTTPException,
    Depends,
    Query,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session


from database import init_db, get_db
from models import User, Contract, Analysis, EmailOTP
from dotenv import load_dotenv

from auth import (
    hash_password,
    verify_password,
    create_access_token,
    get_current_user,
    generate_otp,
)


# ============================================================
# CONFIGURATION
# ============================================================

BASE_DIR = Path(__file__).resolve().parent.parent

load_dotenv(BASE_DIR / ".env")

SMTP_HOST = os.getenv("SMTP_HOST", "smtp.gmail.com")
SMTP_PORT = int(os.getenv("SMTP_PORT", "587"))
SMTP_USERNAME = os.getenv("SMTP_USERNAME", "")
SMTP_PASSWORD = os.getenv("SMTP_PASSWORD", "")
SMTP_FROM = os.getenv("SMTP_FROM", SMTP_USERNAME)

HF_MODEL_ID = os.getenv(
    "HF_MODEL_ID",
    "praveen9052/contractiq-clause-classifier",
)

HF_TOKEN = os.getenv("HF_TOKEN", "")

HF_API_URL = (
    f"https://api-inference.huggingface.co/models/"
    f"{HF_MODEL_ID}"
)

TESSERACT_PATH = os.getenv(
    "TESSERACT_PATH",
    r"C:\Program Files\Tesseract-OCR\tesseract.exe",
)

STORAGE_DIR = (
    BASE_DIR
    / "data"
    / "contract_storage"
)

STORAGE_DIR.mkdir(
    parents=True,
    exist_ok=True,
)

pytesseract.pytesseract.tesseract_cmd = TESSERACT_PATH

MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_CLAUSE_SEGMENTS = 300
CLASSIFICATION_BATCH_SIZE = 8
MIN_CLAUSE_CONFIDENCE = 0.55
MIN_CONTRACT_SIGNALS = 2

OTP_EXPIRY_MINUTES = 10
MAX_OTP_ATTEMPTS = 5


# ============================================================
# APPLICATION
# ============================================================

app = FastAPI(
    title="Contract Intelligence API",
    description=(
        "AI-powered Contract Intelligence platform "
        "using Legal-BERT"
    ),
    version="3.1.0",
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
        "http://localhost:5175",
        "http://127.0.0.1:5175",
        "http://localhost:5176",
        "http://127.0.0.1:5176",
        "http://localhost:5177",
        "http://127.0.0.1:5177",
        "http://localhost:5178",
        "http://127.0.0.1:5178",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# DATABASE
# ============================================================

init_db()


# ============================================================
# MODEL
# ============================================================

# Production inference is performed by the Hugging Face hosted model.
# This keeps the Vercel serverless function below its bundle-size limit.

def check_model_configuration():
    return bool(HF_MODEL_ID)


check_model_configuration()


# ============================================================
# AUTHENTICATION SCHEMAS
# ============================================================

class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    password: str
    company: Optional[str] = None


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileUpdateRequest(BaseModel):
    name: Optional[str] = None
    company: Optional[str] = None


class ChangePasswordRequest(BaseModel):
    current_password: str
    new_password: str


class ForgotPasswordRequest(BaseModel):
    email: EmailStr


class VerifyOTPRequest(BaseModel):
    email: EmailStr
    otp: str


class ResetPasswordRequest(BaseModel):
    email: EmailStr
    otp: str
    new_password: str


class ContractUpdateRequest(BaseModel):
    status: Optional[str] = None
    favorite: Optional[bool] = None
    folder: Optional[str] = None


# ============================================================
# PASSWORD VALIDATION
# ============================================================

def validate_password(password: str):
    if len(password) < 8:
        raise HTTPException(
            status_code=400,
            detail=(
                "Password must contain at least "
                "8 characters."
            ),
        )


# ============================================================
# OTP HELPERS
# ============================================================

def hash_otp(otp: str) -> str:
    return hashlib.sha256(
        otp.encode("utf-8")
    ).hexdigest()


def invalidate_previous_reset_otps(
    user_id: int,
    db: Session,
):
    previous_otps = (
        db.query(EmailOTP)
        .filter(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == "password_reset",
            EmailOTP.used == False,
        )
        .all()
    )

    for otp_record in previous_otps:
        otp_record.used = True


def get_latest_active_reset_otp(
    user_id: int,
    db: Session,
):
    return (
        db.query(EmailOTP)
        .filter(
            EmailOTP.user_id == user_id,
            EmailOTP.purpose == "password_reset",
            EmailOTP.used == False,
        )
        .order_by(
            EmailOTP.created_at.desc()
        )
        .first()
    )


# ============================================================
# GENERAL HELPERS
# ============================================================

def clean_text(text: str) -> str:
    if not text:
        return ""

    text = text.replace(
        "\x00",
        " ",
    )

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


def safe_filename(filename: str) -> str:
    name = Path(
        filename or "contract"
    ).name

    name = re.sub(
        r"[^A-Za-z0-9._-]+",
        "_",
        name,
    )

    return name[:180] or "contract"


def user_storage_directory(
    user_id: int,
) -> Path:

    directory = (
        STORAGE_DIR
        / str(user_id)
    )

    directory.mkdir(
        parents=True,
        exist_ok=True,
    )

    return directory


def serialize_user(user: User):
    return {
        "id": user.id,
        "name": user.name,
        "email": user.email,
        "company": user.company,
        "email_verified": user.email_verified,
        "created_at": (
            user.created_at.isoformat()
            if user.created_at
            else None
        ),
    }


def serialize_contract(
    contract: Contract,
):
    return {
        "id": contract.id,
        "filename": contract.filename,
        "folder": contract.folder,
        "status": contract.status,
        "favorite": contract.favorite,
        "risk_score": contract.risk_score,
        "risk_level": contract.risk_level,
        "created_at": (
            contract.created_at.isoformat()
            if contract.created_at
            else None
        ),
        "updated_at": (
            contract.updated_at.isoformat()
            if contract.updated_at
            else None
        ),
    }


# ============================================================
# PDF EXTRACTION
# ============================================================

def extract_pdf_text(
    file_bytes: bytes,
) -> tuple[str, bool]:

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

    extracted_pages = []
    ocr_used = False

    for page in pdf:

        text = page.get_text(
            "text"
        )

        if text and text.strip():

            extracted_pages.append(
                text
            )

            continue

        try:

            pix = page.get_pixmap(
                matrix=fitz.Matrix(
                    2,
                    2,
                ),
                alpha=False,
            )

            image = Image.open(
                io.BytesIO(
                    pix.tobytes("png")
                )
            )

            ocr_text = (
                pytesseract.image_to_string(
                    image
                )
            )

            extracted_pages.append(
                ocr_text or ""
            )

            ocr_used = True

        except Exception:

            extracted_pages.append("")

    pdf.close()

    text = "\n".join(
        extracted_pages
    )

    return (
        clean_text(text),
        ocr_used,
    )


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

            parts.append(
                paragraph.text
            )

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

    suffix = Path(
        filename
    ).suffix.lower()

    if suffix == ".pdf":

        return extract_pdf_text(
            file_bytes
        )

    if suffix == ".docx":

        return (
            extract_docx_text(
                file_bytes
            ),
            False,
        )

    raise HTTPException(
        status_code=400,
        detail=(
            "Only PDF and DOCX files "
            "are supported."
        ),
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

    for (
        signal_name,
        patterns,
    ) in CONTRACT_SIGNAL_PATTERNS.items():

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
        dict.fromkeys(
            signals
        )
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

    chunks = re.split(
        r"\n\s*\n+",
        text,
    )

    segments = []

    for chunk in chunks:

        chunk = clean_text(
            chunk
        )

        if len(chunk) < 80:
            continue

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

            if len(
                current.strip()
            ) >= 80:

                segments.append(
                    current.strip()
                )

        else:

            segments.append(
                chunk
            )

    return segments[
        :MAX_CLAUSE_SEGMENTS
    ]


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

    return (
        f"Class {class_id}"
    )


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
) -> tuple[
    float,
    str,
    List[Dict[str, Any]],
]:

    findings = []
    contributions = []

    for clause in clauses:

        label = clause[
            "label"
        ]

        confidence = float(
            clause[
                "confidence"
            ]
        )

        weight = RISK_WEIGHTS.get(
            label,
            20,
        )

        contribution = (
            confidence
            * weight
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

        return (
            0.0,
            "LOW",
            findings,
        )

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
        key=lambda item:
        item[
            "risk_contribution"
        ],
        reverse=True,
    )

    return (
        round(
            risk_score,
            1,
        ),
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
                    "text": match.group(
                        0
                    ),
                }
            )

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
                "text": match.group(
                    0
                ),
            }
        )

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

            value = (
                match.group(
                    0
                ).strip()
            )

            if len(value) <= 150:

                entities.append(
                    {
                        "type": "JURISDICTION",
                        "text": value,
                    }
                )

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
                        ).strip()
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
                    match.group(
                        1
                    ).strip()
                )

                entities.append(
                    {
                        "type": "PARTY",
                        "text": value,
                    }
                )

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

    return unique_entities[
        :100
    ]


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

    if not HF_TOKEN:
        print("[MODEL] HF_TOKEN is not configured.")
        return []

    results = []

    headers = {
        "Authorization": f"Bearer {HF_TOKEN}",
        "Content-Type": "application/json",
    }

    for text in relevant_segments:

        payload = {
            "inputs": text[:3000],
            "options": {
                "wait_for_model": True
            }
        }

        try:
            response = requests.post(
                HF_API_URL,
                headers=headers,
                json=payload,
                timeout=60,
            )

            if response.status_code != 200:
                print(
                    f"[MODEL] Hugging Face returned "
                    f"{response.status_code}: {response.text[:500]}"
                )
                continue

            prediction = response.json()

            # Text-classification inference normally returns:
            # [[{"label": "...", "score": 0.95}, ...]]
            if (
                isinstance(prediction, list)
                and prediction
                and isinstance(prediction[0], list)
            ):
                prediction = prediction[0]

            if not isinstance(prediction, list) or not prediction:
                continue

            best = max(
                prediction,
                key=lambda item: float(
                    item.get("score", 0)
                ),
            )

            confidence = float(
                best.get("score", 0)
            )

            if confidence < MIN_CLAUSE_CONFIDENCE:
                continue

            raw_label = str(
                best.get("label", "")
            )

            # Prefer the trained model's explicit label when it
            # corresponds to our known CUAD label list.
            label = raw_label

            if raw_label.startswith("LABEL_"):
                try:
                    class_id = int(
                        raw_label.split("_")[-1]
                    )
                    label = get_label_name(class_id)
                except (ValueError, IndexError):
                    class_id = -1
            else:
                class_id = -1

                normalized = raw_label.lower().strip()

                for index, known_label in enumerate(
                    DEFAULT_LABEL_NAMES
                ):
                    if known_label.lower() == normalized:
                        class_id = index
                        label = known_label
                        break

            results.append(
                {
                    "label": label,
                    "confidence": round(
                        confidence,
                        4,
                    ),
                    "class_id": int(class_id),
                    "text": text[:3000],
                }
            )

        except requests.RequestException as exc:
            print(
                f"[MODEL] Hugging Face request failed: {exc}"
            )

        except Exception as exc:
            print(
                f"[MODEL] Classification error: {exc}"
            )

    return results


# ============================================================
# CORE ANALYSIS ENGINE
# ============================================================

async def perform_contract_analysis(
    filename: str,
    file_bytes: bytes,
):

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

    if not file_bytes:

        raise HTTPException(
            status_code=400,
            detail=(
                "The uploaded file "
                "is empty."
            ),
        )

    if len(file_bytes) > MAX_FILE_SIZE:

        raise HTTPException(
            status_code=413,
            detail=(
                "The uploaded file exceeds "
                "the 50 MB limit."
            ),
        )

    text, ocr_used = (
        extract_document(
            filename,
            file_bytes,
        )
    )

    if len(text) < 50:

        raise HTTPException(
            status_code=400,
            detail={
                "message": (
                    "Unable to extract enough "
                    "text from the uploaded "
                    "document."
                ),
                "document_type": (
                    "unreadable"
                ),
                "ocr_used": ocr_used,
            },
        )

    contract_detection = (
        detect_contract(text)
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
                "document_type": (
                    "non_contract"
                ),
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

    (
        risk_score,
        risk_level,
        findings,
    ) = calculate_risk(
        clauses
    )

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
                "name": clause[
                    "label"
                ],
                "confidence": clause[
                    "confidence"
                ],
                "class_id": clause[
                    "class_id"
                ],
                "text": clause[
                    "text"
                ],
                "status": status,
                "description": (
                    "Clause detected by the "
                    "Legal-BERT classifier."
                ),
            }
        )

    result = {
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
            "model_classes": len(DEFAULT_LABEL_NAMES),
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

    return result


# ============================================================
# AUTHENTICATION
# ============================================================

@app.post(
    "/api/auth/register"
)
def register_user(
    request: RegisterRequest,
    db: Session = Depends(
        get_db
    ),
):

    email = (
        request.email
        .lower()
        .strip()
    )

    existing_user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if existing_user:

        raise HTTPException(
            status_code=400,
            detail=(
                "An account with this "
                "email already exists."
            ),
        )

    if not request.name.strip():

        raise HTTPException(
            status_code=400,
            detail="Name is required.",
        )

    validate_password(
        request.password
    )

    user = User(
        name=request.name.strip(),
        email=email,
        company=(
            request.company.strip()
            if request.company
            else None
        ),
        password_hash=hash_password(
            request.password
        ),
        email_verified=False,
    )

    db.add(user)
    db.commit()
    db.refresh(user)

    token = create_access_token(
        user.id
    )

    return {
        "message": (
            "Account created successfully."
        ),
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(
            user
        ),
    }


@app.post(
    "/api/auth/login"
)
def login_user(
    request: LoginRequest,
    db: Session = Depends(
        get_db
    ),
):

    email = (
        request.email
        .lower()
        .strip()
    )

    user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email or password."
            ),
        )

    if not verify_password(
        request.password,
        user.password_hash,
    ):

        raise HTTPException(
            status_code=401,
            detail=(
                "Invalid email or password."
            ),
        )

    token = create_access_token(
        user.id
    )

    return {
        "message": "Login successful.",
        "access_token": token,
        "token_type": "bearer",
        "user": serialize_user(
            user
        ),
    }


@app.get(
    "/api/auth/me"
)
def get_my_profile(
    current_user: User = Depends(
        get_current_user
    ),
):

    return serialize_user(
        current_user
    )


@app.put(
    "/api/auth/profile"
)
def update_profile(
    request: ProfileUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    if request.name is not None:

        if not request.name.strip():

            raise HTTPException(
                status_code=400,
                detail=(
                    "Name cannot be empty."
                ),
            )

        current_user.name = (
            request.name.strip()
        )

    if request.company is not None:

        current_user.company = (
            request.company.strip()
        )

    db.commit()
    db.refresh(
        current_user
    )

    return {
        "message": (
            "Profile updated successfully."
        ),
        "user": serialize_user(
            current_user
        ),
    }


@app.put(
    "/api/auth/change-password"
)
def change_password(
    request: ChangePasswordRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    if not verify_password(
        request.current_password,
        current_user.password_hash,
    ):

        raise HTTPException(
            status_code=400,
            detail=(
                "Current password is incorrect."
            ),
        )

    validate_password(
        request.new_password
    )

    current_user.password_hash = (
        hash_password(
            request.new_password
        )
    )

    db.commit()

    return {
        "message": (
            "Password changed successfully."
        )
    }


# ============================================================
# FORGOT PASSWORD / OTP
# ============================================================

@app.post(
    "/api/auth/forgot-password"
)
def forgot_password(
    request: ForgotPasswordRequest,
    db: Session = Depends(
        get_db
    ),
):

    email = (
        request.email
        .lower()
        .strip()
    )

    user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    # Security-friendly response:
    # do not reveal whether an account exists.
    generic_message = (
        "If an account exists for this email, "
        "a verification code has been generated."
    )

    if not user:

        return {
            "message": generic_message,
        }

    # Invalidate previous active OTPs.
    invalidate_previous_reset_otps(
        user.id,
        db,
    )

    otp = generate_otp()

    otp_record = EmailOTP(
        user_id=user.id,
        purpose="password_reset",
        otp_hash=hash_otp(otp),
        expires_at=(
            datetime.utcnow()
            + timedelta(
                minutes=OTP_EXPIRY_MINUTES
            )
        ),
        attempts=0,
        used=False,
    )

    db.add(otp_record)
    db.commit()

    # ========================================================
    # REAL EMAIL DELIVERY
    # ========================================================
    if not SMTP_USERNAME or not SMTP_PASSWORD or not SMTP_FROM:
        # Keep the API safe: never expose the OTP in the response.
        # Configure SMTP credentials in the project .env file.
        raise HTTPException(
            status_code=500,
            detail=(
                "Email service is not configured. "
                "Add SMTP_USERNAME, SMTP_PASSWORD and SMTP_FROM to .env."
            ),
        )

    message = EmailMessage()
    message["Subject"] = "ContractIQ Password Reset Code"
    message["From"] = SMTP_FROM
    message["To"] = user.email
    message.set_content(
        f"Hello {user.name or 'there'},\n\n"
        f"Your ContractIQ password reset verification code is: {otp}\n\n"
        f"This code expires in {OTP_EXPIRY_MINUTES} minutes.\n\n"
        "If you did not request a password reset, you can safely ignore this email.\n\n"
        "ContractIQ"
    )

    try:
        with smtplib.SMTP(SMTP_HOST, SMTP_PORT, timeout=20) as server:
            server.starttls()
            server.login(SMTP_USERNAME, SMTP_PASSWORD)
            server.send_message(message)
    except Exception as exc:
        # Do not leave an unusable OTP active if delivery failed.
        otp_record.used = True
        db.commit()
        print(f"[EMAIL] Password reset email failed: {exc}")
        raise HTTPException(
            status_code=502,
            detail=(
                "Unable to send the verification email right now. "
                "Please check the SMTP configuration."
            ),
        )

    print(f"[EMAIL] Password reset OTP sent to {user.email}")

    return {
        "message": (
            "If an account exists for this email, "
            "a verification code has been sent."
        ),
    }


@app.post(
    "/api/auth/verify-otp"
)
def verify_otp(
    request: VerifyOTPRequest,
    db: Session = Depends(
        get_db
    ),
):

    email = (
        request.email
        .lower()
        .strip()
    )

    user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid verification code."
            ),
        )

    otp_record = (
        get_latest_active_reset_otp(
            user.id,
            db,
        )
    )

    if not otp_record:

        raise HTTPException(
            status_code=400,
            detail=(
                "No active verification code. "
                "Please request a new code."
            ),
        )

    if (
        datetime.utcnow()
        > otp_record.expires_at
    ):

        otp_record.used = True
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "This verification code has "
                "expired. Please request a new one."
            ),
        )

    if (
        otp_record.attempts
        >= MAX_OTP_ATTEMPTS
    ):

        otp_record.used = True
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "Too many incorrect attempts. "
                "Please request a new code."
            ),
        )

    submitted_hash = hash_otp(
        request.otp.strip()
    )

    if not secrets.compare_digest(
        submitted_hash,
        otp_record.otp_hash,
    ):

        otp_record.attempts += 1
        db.commit()

        remaining = (
            MAX_OTP_ATTEMPTS
            - otp_record.attempts
        )

        raise HTTPException(
            status_code=400,
            detail=(
                f"Invalid verification code. "
                f"{remaining} attempt(s) remaining."
            ),
        )

    return {
        "message": (
            "Verification code accepted."
        ),
        "verified": True,
    }


@app.post(
    "/api/auth/reset-password"
)
def reset_password(
    request: ResetPasswordRequest,
    db: Session = Depends(
        get_db
    ),
):

    email = (
        request.email
        .lower()
        .strip()
    )

    user = (
        db.query(User)
        .filter(
            User.email == email
        )
        .first()
    )

    if not user:

        raise HTTPException(
            status_code=400,
            detail=(
                "Unable to reset password."
            ),
        )

    validate_password(
        request.new_password
    )

    otp_record = (
        get_latest_active_reset_otp(
            user.id,
            db,
        )
    )

    if not otp_record:

        raise HTTPException(
            status_code=400,
            detail=(
                "No active verification code. "
                "Please request a new one."
            ),
        )

    if (
        datetime.utcnow()
        > otp_record.expires_at
    ):

        otp_record.used = True
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "This verification code has "
                "expired. Please request a new one."
            ),
        )

    if (
        otp_record.attempts
        >= MAX_OTP_ATTEMPTS
    ):

        otp_record.used = True
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "Too many incorrect attempts. "
                "Please request a new code."
            ),
        )

    submitted_hash = hash_otp(
        request.otp.strip()
    )

    if not secrets.compare_digest(
        submitted_hash,
        otp_record.otp_hash,
    ):

        otp_record.attempts += 1
        db.commit()

        raise HTTPException(
            status_code=400,
            detail=(
                "Invalid verification code."
            ),
        )

    user.password_hash = hash_password(
        request.new_password
    )

    otp_record.used = True

    db.commit()

    return {
        "message": (
            "Password reset successfully. "
            "You can now sign in with your "
            "new password."
        )
    }


# ============================================================
# CONTRACT ANALYSIS
# ============================================================

@app.post(
    "/api/contracts/analyze"
)
async def analyze_contract(
    file: UploadFile = File(...),
):

    filename = (
        file.filename
        or ""
    )

    file_bytes = await file.read()

    return await perform_contract_analysis(
        filename,
        file_bytes,
    )


# ============================================================
# SAVED CONTRACT ANALYSIS
# ============================================================

@app.post(
    "/api/contracts/analyze-and-save"
)
async def analyze_and_save_contract(
    file: UploadFile = File(...),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    filename = (
        file.filename
        or "contract"
    )

    file_bytes = await file.read()

    result = await perform_contract_analysis(
        filename,
        file_bytes,
    )

    user_dir = user_storage_directory(
        current_user.id
    )

    contract = Contract(
        user_id=current_user.id,
        filename=filename,
        folder="General",
        status="Pending Review",
        favorite=False,
        risk_score=int(
            round(
                result[
                    "risk_score"
                ]
            )
        ),
        risk_level=result[
            "risk_level"
        ],
    )

    db.add(contract)
    db.commit()
    db.refresh(contract)

    stored_filename = (
        f"{contract.id}_"
        f"{safe_filename(filename)}"
    )

    stored_path = (
        user_dir
        / stored_filename
    )

    with open(
        stored_path,
        "wb",
    ) as output_file:

        output_file.write(
            file_bytes
        )

    contract.stored_path = str(
        stored_path
    )

    analysis = Analysis(
        contract_id=contract.id,
        result_json=json.dumps(
            result,
            ensure_ascii=False,
        ),
    )

    db.add(analysis)

    db.commit()

    result["contract_id"] = (
        contract.id
    )

    result["saved"] = True

    return result


# ============================================================
# MULTI-FILE UPLOAD
# ============================================================

@app.post(
    "/api/contracts/analyze-many"
)
async def analyze_many_contracts(
    files: List[UploadFile] = File(...),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    if not files:

        raise HTTPException(
            status_code=400,
            detail=(
                "No contract files "
                "were uploaded."
            ),
        )

    results = []

    for file in files:

        try:

            filename = (
                file.filename
                or "contract"
            )

            file_bytes = (
                await file.read()
            )

            result = (
                await perform_contract_analysis(
                    filename,
                    file_bytes,
                )
            )

            user_dir = (
                user_storage_directory(
                    current_user.id
                )
            )

            contract = Contract(
                user_id=current_user.id,
                filename=filename,
                folder="General",
                status="Pending Review",
                favorite=False,
                risk_score=int(
                    round(
                        result[
                            "risk_score"
                        ]
                    )
                ),
                risk_level=result[
                    "risk_level"
                ],
            )

            db.add(contract)
            db.commit()
            db.refresh(contract)

            stored_filename = (
                f"{contract.id}_"
                f"{safe_filename(filename)}"
            )

            stored_path = (
                user_dir
                / stored_filename
            )

            with open(
                stored_path,
                "wb",
            ) as output_file:

                output_file.write(
                    file_bytes
                )

            contract.stored_path = (
                str(stored_path)
            )

            analysis = Analysis(
                contract_id=contract.id,
                result_json=json.dumps(
                    result,
                    ensure_ascii=False,
                ),
            )

            db.add(analysis)
            db.commit()

            result[
                "contract_id"
            ] = contract.id

            result[
                "saved"
            ] = True

            results.append(
                {
                    "success": True,
                    "result": result,
                }
            )

        except HTTPException as exc:

            results.append(
                {
                    "success": False,
                    "filename": (
                        file.filename
                    ),
                    "error": str(
                        exc.detail
                    ),
                }
            )

        except Exception as exc:

            results.append(
                {
                    "success": False,
                    "filename": (
                        file.filename
                    ),
                    "error": str(
                        exc
                    ),
                }
            )

    return {
        "total": len(files),
        "successful": sum(
            1
            for item in results
            if item["success"]
        ),
        "failed": sum(
            1
            for item in results
            if not item["success"]
        ),
        "results": results,
    }


# ============================================================
# CONTRACT LIBRARY
# ============================================================

@app.get(
    "/api/contracts"
)
def list_contracts(
    search: Optional[str] = Query(
        default=None
    ),
    favorite: Optional[bool] = Query(
        default=None
    ),
    status: Optional[str] = Query(
        default=None
    ),
    folder: Optional[str] = Query(
        default=None
    ),
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    query = (
        db.query(Contract)
        .filter(
            Contract.user_id
            == current_user.id
        )
    )

    if search:

        search_value = (
            f"%{search.strip()}%"
        )

        query = query.filter(
            Contract.filename.ilike(
                search_value
            )
        )

    if favorite is not None:

        query = query.filter(
            Contract.favorite
            == favorite
        )

    if status:

        query = query.filter(
            Contract.status
            == status
        )

    if folder:

        query = query.filter(
            Contract.folder
            == folder
        )

    contracts = (
        query
        .order_by(
            Contract.updated_at.desc()
        )
        .all()
    )

    return {
        "count": len(contracts),
        "contracts": [
            serialize_contract(
                contract
            )
            for contract in contracts
        ],
    }


# ============================================================
# SINGLE CONTRACT
# ============================================================

@app.get(
    "/api/contracts/{contract_id}"
)
def get_contract(
    contract_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    contract = (
        db.query(Contract)
        .filter(
            Contract.id
            == contract_id,
            Contract.user_id
            == current_user.id,
        )
        .first()
    )

    if not contract:

        raise HTTPException(
            status_code=404,
            detail=(
                "Contract not found."
            ),
        )

    analysis = (
        db.query(Analysis)
        .filter(
            Analysis.contract_id
            == contract.id
        )
        .order_by(
            Analysis.created_at.desc()
        )
        .first()
    )

    result = None

    if analysis:

        try:

            result = json.loads(
                analysis.result_json
            )

        except json.JSONDecodeError:

            result = None

    return {
        "contract": (
            serialize_contract(
                contract
            )
        ),
        "analysis": result,
    }


# ============================================================
# UPDATE CONTRACT
# ============================================================

@app.patch(
    "/api/contracts/{contract_id}"
)
def update_contract(
    contract_id: int,
    request: ContractUpdateRequest,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    contract = (
        db.query(Contract)
        .filter(
            Contract.id
            == contract_id,
            Contract.user_id
            == current_user.id,
        )
        .first()
    )

    if not contract:

        raise HTTPException(
            status_code=404,
            detail=(
                "Contract not found."
            ),
        )

    allowed_statuses = {
        "Pending Review",
        "Under Review",
        "Reviewed",
        "Approved",
        "Rejected",
    }

    if request.status is not None:

        if (
            request.status
            not in allowed_statuses
        ):

            raise HTTPException(
                status_code=400,
                detail=(
                    "Invalid contract status."
                ),
            )

        contract.status = (
            request.status
        )

    if request.favorite is not None:

        contract.favorite = (
            request.favorite
        )

    if request.folder is not None:

        folder = (
            request.folder
            .strip()
        )

        contract.folder = (
            folder
            if folder
            else "General"
        )

    db.commit()
    db.refresh(contract)

    return {
        "message": (
            "Contract updated successfully."
        ),
        "contract": (
            serialize_contract(
                contract
            )
        ),
    }


# ============================================================
# DELETE CONTRACT
# ============================================================

@app.delete(
    "/api/contracts/{contract_id}"
)
def delete_contract(
    contract_id: int,
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    contract = (
        db.query(Contract)
        .filter(
            Contract.id
            == contract_id,
            Contract.user_id
            == current_user.id,
        )
        .first()
    )

    if not contract:

        raise HTTPException(
            status_code=404,
            detail=(
                "Contract not found."
            ),
        )

    if contract.stored_path:

        stored_path = Path(
            contract.stored_path
        )

        if stored_path.exists():

            try:
                stored_path.unlink()

            except Exception:
                pass

    db.query(Analysis).filter(
        Analysis.contract_id
        == contract.id
    ).delete(
        synchronize_session=False
    )

    db.delete(contract)

    db.commit()

    return {
        "message": (
            "Contract deleted successfully."
        )
    }


# ============================================================
# DASHBOARD STATISTICS
# ============================================================

@app.get(
    "/api/dashboard"
)
def dashboard(
    current_user: User = Depends(
        get_current_user
    ),
    db: Session = Depends(
        get_db
    ),
):

    contracts = (
        db.query(Contract)
        .filter(
            Contract.user_id
            == current_user.id
        )
        .all()
    )

    total = len(contracts)

    high = sum(
        1
        for contract in contracts
        if contract.risk_level
        and contract.risk_level.upper()
        == "HIGH"
    )

    medium = sum(
        1
        for contract in contracts
        if contract.risk_level
        and contract.risk_level.upper()
        == "MEDIUM"
    )

    low = sum(
        1
        for contract in contracts
        if contract.risk_level
        and contract.risk_level.upper()
        == "LOW"
    )

    scored = [
        float(contract.risk_score)
        for contract in contracts
        if contract.risk_score
        is not None
    ]

    average_risk = (
        round(
            sum(scored)
            / len(scored),
            1,
        )
        if scored
        else 0
    )

    recent = sorted(
        contracts,
        key=lambda contract:
        contract.updated_at
        or datetime.min,
        reverse=True,
    )[:5]

    return {
        "total_contracts": total,
        "high_risk": high,
        "medium_risk": medium,
        "low_risk": low,
        "average_risk": average_risk,
        "recent_contracts": [
            serialize_contract(
                contract
            )
            for contract in recent
        ],
    }


# ============================================================
# HEALTH
# ============================================================

@app.get(
    "/health"
)
def health():

    return {
        "status": "ok",
        "service": (
            "contract-intelligence-api"
        ),
        "model_loaded": bool(HF_TOKEN),
        "model_classes": len(DEFAULT_LABEL_NAMES),
        "ocr_available": Path(
            TESSERACT_PATH
        ).exists(),
        "database": "connected",
        "version": "3.1.0",
        "authentication": True,
        "password_reset": True,
        "otp_mode": "smtp",
    }
