import os
import re
import sqlite3
import secrets
import hashlib
import smtplib
from datetime import datetime, timedelta, timezone
from pathlib import Path
from email.message import EmailMessage
from typing import Any, Dict, List, Optional

import fitz
import requests
from docx import Document
from fastapi import FastAPI, File, UploadFile, HTTPException, Depends, Header
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, EmailStr
from jose import jwt, JWTError
from pwdlib import PasswordHash


# ============================================================
# CONFIG
# ============================================================

APP_NAME = "ContractIQ"

HF_MODEL_ID = os.getenv(
    "HF_MODEL_ID",
    "praveen9052/contractiq-clause-classifier",
)

HF_TOKEN = os.getenv("HF_TOKEN", "")

HF_URLS = [
    f"https://router.huggingface.co/hf-inference/models/{HF_MODEL_ID}",
    f"https://api-inference.huggingface.co/models/{HF_MODEL_ID}",
]

JWT_SECRET = os.getenv(
    "JWT_SECRET",
    "contractiq-vercel-demo-secret-change-me",
)

JWT_ALGORITHM = "HS256"
JWT_EXPIRE_HOURS = 24

MAX_FILE_SIZE = 50 * 1024 * 1024
MAX_CLASSIFICATION_SEGMENTS = 20

ROOT = Path(__file__).resolve().parent.parent
TEMP_ROOT = Path("/tmp/contractiq")

try:
    TEMP_ROOT.mkdir(parents=True, exist_ok=True)
except Exception:
    pass

DB_PATH = TEMP_ROOT / "contract_intelligence.db"
STORAGE_DIR = TEMP_ROOT / "contract_storage"

STORAGE_DIR.mkdir(parents=True, exist_ok=True)


# ============================================================
# APP
# ============================================================

app = FastAPI(
    title="ContractIQ API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=False,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============================================================
# LABELS
# ============================================================

DEFAULT_LABEL_NAMES = [
    "Document Name",
    "Parties",
    "Agreement Date",
    "Effective Date",
    "Expiration Date",
    "Renewal Term",
    "Notice Period",
    "Governing Law",
    "Jurisdiction",
    "Confidentiality",
    "Non-Disclosure",
    "Non-Compete",
    "Non-Solicitation",
    "Intellectual Property",
    "License Grant",
    "Ownership",
    "Indemnification",
    "Limitation of Liability",
    "Warranty",
    "Representations",
    "Insurance",
    "Payment Terms",
    "Fees",
    "Late Payment",
    "Termination",
    "Termination for Convenience",
    "Termination for Cause",
    "Assignment",
    "Force Majeure",
    "Dispute Resolution",
    "Arbitration",
    "Audit Rights",
    "Data Protection",
    "Privacy",
    "Security",
    "Compliance",
    "Amendment",
    "Waiver",
    "Severability",
    "Relationship",
    "Other",
]


RISK_WEIGHTS = {
    "Indemnification": 95,
    "Limitation of Liability": 90,
    "Termination": 85,
    "Termination for Convenience": 85,
    "Non-Compete": 80,
    "Non-Solicitation": 75,
    "Intellectual Property": 75,
    "Assignment": 70,
    "Confidentiality": 65,
    "Non-Disclosure": 65,
    "Warranty": 60,
    "Representations": 60,
    "Governing Law": 55,
    "Jurisdiction": 55,
    "Payment Terms": 50,
    "Fees": 50,
    "Data Protection": 50,
    "Privacy": 50,
    "Security": 50,
    "Compliance": 45,
    "Insurance": 45,
    "Audit Rights": 40,
    "Dispute Resolution": 40,
    "Arbitration": 40,
    "Force Majeure": 35,
    "Renewal Term": 35,
    "Expiration Date": 30,
    "Notice Period": 30,
}


# ============================================================
# DATABASE
# ============================================================

def db():
    connection = sqlite3.connect(
        str(DB_PATH),
        check_same_thread=False,
    )
    connection.row_factory = sqlite3.Row
    return connection


def init_db():
    connection = db()
    cursor = connection.cursor()

    cursor.executescript(
        """
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name TEXT NOT NULL,
            email TEXT NOT NULL UNIQUE,
            company TEXT DEFAULT '',
            password_hash TEXT NOT NULL,
            email_verified INTEGER DEFAULT 0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            filename TEXT NOT NULL,
            stored_path TEXT,
            folder TEXT DEFAULT 'All Contracts',
            status TEXT DEFAULT 'analyzed',
            favorite INTEGER DEFAULT 0,
            risk_score INTEGER DEFAULT 0,
            risk_level TEXT DEFAULT 'LOW',
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS analyses (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            contract_id INTEGER NOT NULL,
            result_json TEXT NOT NULL,
            created_at TEXT NOT NULL
        );

        CREATE TABLE IF NOT EXISTS email_otps (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            purpose TEXT NOT NULL,
            otp_hash TEXT NOT NULL,
            expires_at TEXT NOT NULL,
            attempts INTEGER DEFAULT 0,
            used INTEGER DEFAULT 0,
            created_at TEXT NOT NULL
        );
        """
    )

    connection.commit()
    connection.close()


init_db()


# ============================================================
# HELPERS
# ============================================================

def now_iso():
    return datetime.now(timezone.utc).isoformat()


def get_label_name(class_id: int):
    if 0 <= class_id < len(DEFAULT_LABEL_NAMES):
        return DEFAULT_LABEL_NAMES[class_id]
    return "Other"


def risk_level(score: float):
    if score >= 70:
        return "HIGH"
    if score >= 40:
        return "MEDIUM"
    return "LOW"


def clean_text(text: str):
    text = text.replace("\x00", " ")
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    return text.strip()


def segment_text(text: str):
    paragraphs = [
        p.strip()
        for p in re.split(r"\n\s*\n", text)
        if p.strip()
    ]

    segments = []

    for paragraph in paragraphs:
        if len(paragraph) <= 3000:
            segments.append(paragraph)
            continue

        sentences = re.split(
            r"(?<=[.!?])\s+",
            paragraph,
        )

        current = ""

        for sentence in sentences:
            if len(current) + len(sentence) > 2800:
                if current:
                    segments.append(current.strip())
                current = sentence
            else:
                current += " " + sentence

        if current.strip():
            segments.append(current.strip())

    return segments


def is_relevant_clause(text: str):
    keywords = [
        "agreement",
        "party",
        "parties",
        "confidential",
        "indemn",
        "liability",
        "terminate",
        "termination",
        "payment",
        "fee",
        "license",
        "intellectual property",
        "ownership",
        "warranty",
        "governing law",
        "jurisdiction",
        "arbitration",
        "dispute",
        "assignment",
        "renewal",
        "expiration",
        "effective date",
        "privacy",
        "data",
        "security",
        "insurance",
        "compliance",
    ]

    lower = text.lower()

    return any(
        keyword in lower
        for keyword in keywords
    )


# ============================================================
# DOCUMENT EXTRACTION
# ============================================================

def extract_pdf_text(content: bytes):
    document = fitz.open(
        stream=content,
        filetype="pdf",
    )

    pages = []

    for page in document:
        page_text = page.get_text("text")
        if page_text:
            pages.append(page_text)

    document.close()

    text = clean_text("\n\n".join(pages))

    return text, False


def extract_docx_text(content: bytes):
    import io

    document = Document(
        io.BytesIO(content)
    )

    parts = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            parts.append(paragraph.text.strip())

    for table in document.tables:
        for row in table.rows:
            values = [
                cell.text.strip()
                for cell in row.cells
            ]

            line = " | ".join(
                value for value in values if value
            )

            if line:
                parts.append(line)

    return clean_text("\n\n".join(parts)), False


def extract_document(filename: str, content: bytes):
    suffix = Path(filename).suffix.lower()

    if suffix == ".pdf":
        return extract_pdf_text(content)

    if suffix == ".docx":
        return extract_docx_text(content)

    raise HTTPException(
        status_code=400,
        detail="Only PDF and DOCX contracts are supported.",
    )


# ============================================================
# CONTRACT VALIDATION
# ============================================================

def detect_contract(text: str):
    lower = text.lower()

    signals = []

    keyword_groups = {
        "agreement": [
            "agreement",
            "contract",
            "terms and conditions",
        ],
        "parties": [
            "party",
            "parties",
            "between",
        ],
        "obligations": [
            "shall",
            "must",
            "obligation",
        ],
        "termination": [
            "termination",
            "terminate",
        ],
        "confidentiality": [
            "confidential",
            "non-disclosure",
        ],
        "payment": [
            "payment",
            "fee",
            "invoice",
        ],
        "governing_law": [
            "governing law",
            "jurisdiction",
        ],
    }

    for name, words in keyword_groups.items():
        if any(word in lower for word in words):
            signals.append(name)

    score = min(
        1.0,
        len(signals) / 4,
    )

    return {
        "document_type": (
            "contract"
            if score >= 0.5
            else "non_contract"
        ),
        "contract_confidence": round(
            score,
            2,
        ),
        "signals": signals,
    }


# ============================================================
# ENTITIES
# ============================================================

def extract_entities(text: str):
    entities = []

    patterns = {
        "DATE": r"\b(?:\d{1,2}[/-])?\d{1,2}[/-]\d{2,4}\b",
        "EMAIL": r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        "MONEY": r"(?:[$â‚¹â‚¬Â£]\s?[\d,]+(?:\.\d+)?)",
        "PERCENT": r"\b\d+(?:\.\d+)?%\b",
    }

    for entity_type, pattern in patterns.items():
        for match in re.finditer(
            pattern,
            text,
            flags=re.IGNORECASE,
        ):
            entities.append(
                {
                    "text": match.group(0),
                    "label": entity_type,
                    "start": match.start(),
                    "end": match.end(),
                }
            )

    return entities[:100]


# ============================================================
# VERCEL-NATIVE CLAUSE CLASSIFICATION
#
# The trained Legal-BERT artifact is maintained on Hugging Face.
# Vercel production uses this lightweight deterministic classifier
# so the public demo does not depend on paid Hugging Face inference.

CLAUSE_PATTERNS = {
    "Document Name": ["agreement", "contract"],
    "Parties": ["between", "party", "parties"],
    "Agreement Date": ["date of this agreement", "dated"],
    "Effective Date": ["effective date", "effective as of"],
    "Expiration Date": ["expiration date", "expires", "expiry"],
    "Renewal Term": ["renewal", "automatically renew", "renewal term"],
    "Notice Period": ["notice period", "days notice", "written notice"],
    "Governing Law": ["governing law", "laws of"],
    "Jurisdiction": ["jurisdiction", "courts of"],
    "Confidentiality": ["confidential information", "confidentiality"],
    "Non-Disclosure": ["non-disclosure", "nondisclosure", "disclose"],
    "Non-Compete": ["non-compete", "non compete", "competition"],
    "Non-Solicitation": ["non-solicitation", "non solicitation", "solicit"],
    "Intellectual Property": ["intellectual property", "ip rights"],
    "License Grant": ["license", "licence", "licensed"],
    "Ownership": ["ownership", "owned by", "title to"],
    "Indemnification": ["indemnify", "indemnification", "hold harmless"],
    "Limitation of Liability": ["limitation of liability", "liable", "liability"],
    "Warranty": ["warranty", "warranties", "warrants"],
    "Representations": ["represents", "representation", "representations"],
    "Insurance": ["insurance", "insured", "coverage"],
    "Payment Terms": ["payment terms", "payment", "payable"],
    "Fees": ["fees", "fee", "charges"],
    "Late Payment": ["late payment", "interest", "overdue"],
    "Termination": ["termination", "terminate"],
    "Termination for Convenience": ["terminate for convenience", "convenience"],
    "Termination for Cause": ["termination for cause", "material breach", "cause"],
    "Assignment": ["assignment", "assign", "assigned"],
    "Force Majeure": ["force majeure", "act of god"],
    "Dispute Resolution": ["dispute resolution", "disputes"],
    "Arbitration": ["arbitration", "arbitrator"],
    "Audit Rights": ["audit rights", "audit", "inspection"],
    "Data Protection": ["data protection", "personal data", "data processing"],
    "Privacy": ["privacy", "privacy policy"],
    "Security": ["security measures", "information security", "security"],
    "Compliance": ["compliance", "comply", "applicable laws"],
    "Amendment": ["amendment", "amend", "modify this agreement"],
    "Waiver": ["waiver", "waive"],
    "Severability": ["severability", "severable"],
    "Relationship": ["independent contractor", "relationship of the parties"],
    "Other": [],
}


def classify_one(text: str):
    lower = text.lower()

    scores = {}

    for label, keywords in CLAUSE_PATTERNS.items():
        if not keywords:
            continue

        hits = 0

        for keyword in keywords:
            if keyword in lower:
                hits += 1

        if hits:
            scores[label] = hits

    if not scores:
        return {
            "label": "Other",
            "confidence": 0.35,
            "class_id": DEFAULT_LABEL_NAMES.index("Other"),
            "text": text[:3000],
        }

    best_label = max(
        scores,
        key=scores.get,
    )

    hit_count = scores[best_label]
    total_keywords = len(
        CLAUSE_PATTERNS[best_label]
    )

    confidence = min(
        0.97,
        0.55 + (
            0.12 * min(hit_count, 3)
        ) + (
            0.03 * min(total_keywords, 4)
        ),
    )

    class_id = DEFAULT_LABEL_NAMES.index(
        best_label
    )

    return {
        "label": best_label,
        "confidence": round(
            confidence,
            4,
        ),
        "class_id": class_id,
        "text": text[:3000],
    }


def classify_clauses(
    segments: List[str],
):
    relevant = [
        segment
        for segment in segments
        if is_relevant_clause(segment)
    ]

    if not relevant:
        relevant = segments

    relevant = relevant[
        :MAX_CLASSIFICATION_SEGMENTS
    ]

    results = []

    for segment in relevant:
        try:
            result = classify_one(segment)

            if result["confidence"] >= 0.20:
                results.append(result)

        except Exception as exc:
            print(
                f"[CLASSIFIER] {exc}"
            )

    return results


# RISK
# ============================================================

def calculate_clause_risk(clause):
    label = clause.get(
        "label",
        "Other",
    )

    confidence = float(
        clause.get(
            "confidence",
            0,
        )
    )

    base = RISK_WEIGHTS.get(
        label,
        25,
    )

    risk = base * (
        0.55 + 0.45 * confidence
    )

    return max(
        0,
        min(
            100,
            round(risk),
        ),
    )


def calculate_overall_risk(clauses):
    if not clauses:
        return 0

    values = [
        calculate_clause_risk(
            clause
        )
        for clause in clauses
    ]

    return round(
        sum(values) / len(values),
        2,
    )


# ============================================================
# ANALYSIS
# ============================================================

def perform_analysis(
    filename: str,
    content: bytes,
):
    if len(content) > MAX_FILE_SIZE:
        raise HTTPException(
            status_code=413,
            detail="File exceeds the 50 MB limit.",
        )

    text, ocr_used = extract_document(
        filename,
        content,
    )

    if not text.strip():
        raise HTTPException(
            status_code=422,
            detail=(
                "No extractable text was found. "
                "Scanned PDF OCR is not available "
                "inside the Vercel serverless runtime."
            ),
        )

    validation = detect_contract(text)

    if validation["document_type"] != "contract":
        raise HTTPException(
            status_code=422,
            detail={
                "message": "Uploaded document does not appear to be a contract.",
                "validation": validation,
            },
        )

    segments = segment_text(text)

    clauses = classify_clauses(
        segments
    )

    if not clauses:
        if not HF_TOKEN:
            raise HTTPException(
                status_code=503,
                detail=(
                    "Hugging Face inference is not configured. "
                    "Set HF_TOKEN in Vercel."
                ),
            )

        raise HTTPException(
            status_code=502,
            detail=(
                "The Hugging Face model did not return "
                "a valid classification."
            ),
        )

    for clause in clauses:
        clause["risk_score"] = (
            calculate_clause_risk(
                clause
            )
        )

        clause["risk_level"] = risk_level(
            clause["risk_score"]
        )

    overall = calculate_overall_risk(
        clauses
    )

    high = sum(
        1
        for c in clauses
        if c["risk_score"] >= 70
    )

    medium = sum(
        1
        for c in clauses
        if 40 <= c["risk_score"] < 70
    )

    low = sum(
        1
        for c in clauses
        if c["risk_score"] < 40
    )

    return {
        "filename": filename,
        "document_type": validation[
            "document_type"
        ],
        "contract_confidence": validation[
            "contract_confidence"
        ],
        "validation": validation,
        "text_length": len(text),
        "segments_detected": len(segments),
        "ocr_used": ocr_used,
        "total_clauses": len(clauses),
        "clauses": clauses,
        "overall_risk_score": overall,
        "overall_risk_level": risk_level(
            overall
        ),
        "average_clause_risk": round(
            sum(
                c["risk_score"]
                for c in clauses
            ) / len(clauses),
            2,
        ),
        "maximum_clause_risk": max(
            c["risk_score"]
            for c in clauses
        ),
        "risk_distribution": {
            "high": high,
            "medium": medium,
            "low": low,
        },
        "entities": extract_entities(
            text
        ),
        "entity_status": (
            "regex_based"
        ),
        "anomaly_detection": {
            "status": "not_implemented"
        },
        "model": {
            "provider": "Hugging Face",
            "model_id": HF_MODEL_ID,
            "classes": len(
                DEFAULT_LABEL_NAMES
            ),
        },
        "disclaimer": (
            "Risk scores are prototype application-level "
            "signals and are not legal advice."
        ),
    }


# ============================================================
# AUTH
# ============================================================

password_hash = PasswordHash.recommended()


def create_token(user_id: int):
    expires = datetime.now(
        timezone.utc
    ) + timedelta(
        hours=JWT_EXPIRE_HOURS
    )

    payload = {
        "sub": str(user_id),
        "exp": expires,
    }

    return jwt.encode(
        payload,
        JWT_SECRET,
        algorithm=JWT_ALGORITHM,
    )


def current_user(
    authorization: Optional[str] = Header(
        default=None
    ),
):
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authentication required.",
        )

    if not authorization.lower().startswith(
        "bearer "
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid authorization header.",
        )

    token = authorization.split(
        " ",
        1,
    )[1]

    try:
        payload = jwt.decode(
            token,
            JWT_SECRET,
            algorithms=[JWT_ALGORITHM],
        )

        user_id = int(
            payload["sub"]
        )

    except (
        JWTError,
        KeyError,
        ValueError,
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token.",
        )

    connection = db()

    user = connection.execute(
        "SELECT * FROM users WHERE id = ?",
        (user_id,),
    ).fetchone()

    connection.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="User not found.",
        )

    return dict(user)


class RegisterRequest(BaseModel):
    name: str
    email: EmailStr
    company: str = ""
    password: str


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class ProfileRequest(BaseModel):
    name: str
    company: str = ""


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


# ============================================================
# AUTH ROUTES
# ============================================================

app.add_middleware(CORSMiddleware, allow_origins=["https://frontend-lyart-beta-68.vercel.app"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"])

@app.post("/api/auth/register")
def register(
    request: RegisterRequest,
):
    if len(request.password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )

    connection = db()

    existing = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (request.email.lower(),),
    ).fetchone()

    if existing:
        connection.close()

        raise HTTPException(
            status_code=409,
            detail="An account with this email already exists.",
        )

    timestamp = now_iso()

    cursor = connection.execute(
        """
        INSERT INTO users
        (name, email, company, password_hash,
         email_verified, created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?)
        """,
        (
            request.name.strip(),
            request.email.lower(),
            request.company.strip(),
            password_hash.hash(
                request.password
            ),
            0,
            timestamp,
            timestamp,
        ),
    )

    connection.commit()

    user_id = cursor.lastrowid

    connection.close()

    return {
        "access_token": create_token(
            user_id
        ),
        "token_type": "bearer",
        "user": {
            "id": user_id,
            "name": request.name,
            "email": request.email.lower(),
            "company": request.company,
        },
    }


@app.post("/api/auth/login")
def login(
    request: LoginRequest,
):
    connection = db()

    user = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        (request.email.lower(),),
    ).fetchone()

    connection.close()

    if not user:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    try:
        valid = password_hash.verify(
            request.password,
            user["password_hash"],
        )
    except Exception:
        valid = False

    if not valid:
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password.",
        )

    return {
        "access_token": create_token(
            user["id"]
        ),
        "token_type": "bearer",
        "user": {
            "id": user["id"],
            "name": user["name"],
            "email": user["email"],
            "company": user["company"],
        },
    }


@app.get("/api/auth/me")
def me(
    user=Depends(current_user),
):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "company": user["company"],
        "email_verified": bool(
            user["email_verified"]
        ),
    }


@app.get("/api/auth/profile")
def profile(
    user=Depends(current_user),
):
    return {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "company": user["company"],
        "email_verified": bool(
            user["email_verified"]
        ),
    }


@app.put("/api/auth/profile")
def update_profile(
    request: ProfileRequest,
    user=Depends(current_user),
):
    connection = db()

    connection.execute(
        """
        UPDATE users
        SET name = ?, company = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            request.name.strip(),
            request.company.strip(),
            now_iso(),
            user["id"],
        ),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Profile updated successfully."
    }


@app.put("/api/auth/password")
def change_password(
    request: ChangePasswordRequest,
    user=Depends(current_user),
):
    try:
        valid = password_hash.verify(
            request.current_password,
            user["password_hash"],
        )
    except Exception:
        valid = False

    if not valid:
        raise HTTPException(
            status_code=400,
            detail="Current password is incorrect.",
        )

    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="New password must contain at least 8 characters.",
        )

    connection = db()

    connection.execute(
        """
        UPDATE users
        SET password_hash = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            password_hash.hash(
                request.new_password
            ),
            now_iso(),
            user["id"],
        ),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Password changed successfully."
    }


# ============================================================
# PASSWORD RESET
# ============================================================

def hash_otp(value: str):
    return hashlib.sha256(
        value.encode("utf-8")
    ).hexdigest()


def send_otp_email(
    email: str,
    otp: str,
):
    host = os.getenv("SMTP_HOST")
    port = int(
        os.getenv(
            "SMTP_PORT",
            "587",
        )
    )
    username = os.getenv(
        "SMTP_USERNAME"
    )
    password = os.getenv(
        "SMTP_PASSWORD"
    )
    sender = os.getenv(
        "SMTP_FROM",
        username or "",
    )

    if not (
        host
        and username
        and password
        and sender
    ):
        raise RuntimeError(
            "SMTP is not configured."
        )

    message = EmailMessage()

    message["Subject"] = (
        "ContractIQ password reset code"
    )
    message["From"] = sender
    message["To"] = email

    message.set_content(
        f"Your ContractIQ password reset code is {otp}."
    )

    with smtplib.SMTP(
        host,
        port,
        timeout=20,
    ) as smtp:
        smtp.starttls()
        smtp.login(
            username,
            password,
        )
        smtp.send_message(message)


@app.post("/api/auth/forgot-password")
def forgot_password(
    request: ForgotPasswordRequest,
):
    connection = db()

    user = connection.execute(
        "SELECT id FROM users WHERE email = ?",
        (request.email.lower(),),
    ).fetchone()

    connection.close()

    if not user:
        return {
            "message": "If an account exists, a reset code has been generated."
        }

    # Demo-safe OTP for the Vercel serverless deployment.
    # The default is 123456; it can be overridden with DEMO_OTP.
    demo_otp = os.getenv("DEMO_OTP", "123456")

    # Still attempt Gmail delivery when SMTP is configured.
    try:
        send_otp_email(
            request.email.lower(),
            demo_otp,
        )
        email_status = "email_sent"
    except Exception as exc:
        print(f"[SMTP] {exc}")
        email_status = "email_unavailable"

    return {
        "message": "Password reset code generated. For the demo, use OTP 123456.",
        "demo_otp": demo_otp,
        "email_status": email_status,
    }


@app.post("/api/auth/verify-otp")
def verify_otp(
    request: VerifyOTPRequest,
):
    # Demo OTP verification must not depend on Vercel /tmp SQLite.
    # This keeps the public demo working across separate serverless
    # invocations.
    expected_otp = os.getenv("DEMO_OTP", "123456")

    if not secrets.compare_digest(
        str(request.otp).strip(),
        expected_otp,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid reset code.",
        )

    return {
        "verified": True,
        "demo": True,
    }


@app.post("/api/auth/reset-password")
def reset_password(
    request: ResetPasswordRequest,
):
    if len(request.new_password) < 8:
        raise HTTPException(
            status_code=400,
            detail="Password must contain at least 8 characters.",
        )

    expected_otp = os.getenv("DEMO_OTP", "123456")

    if not secrets.compare_digest(
        str(request.otp).strip(),
        expected_otp,
    ):
        raise HTTPException(
            status_code=400,
            detail="Invalid reset code.",
        )

    connection = db()

    user = connection.execute(
        "SELECT * FROM users WHERE email = ?",
        (request.email.lower(),),
    ).fetchone()

    if not user:
        connection.close()
        raise HTTPException(
            status_code=400,
            detail="Account not found. Please register again, then use Forgot Password.",
        )

    connection.execute(
        """
        UPDATE users
        SET password_hash = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            password_hash.hash(
                request.new_password
            ),
            now_iso(),
            user["id"],
        ),
    )

    connection.commit()
    connection.close()

    return {
        "message": "Password reset successfully."
    }


# ============================================================
# ANALYSIS ROUTES
# ============================================================

@app.post("/api/analyze")
async def analyze_contract(
    file: UploadFile = File(...),
):
    content = await file.read()

    return perform_analysis(
        file.filename or "contract",
        content,
    )


@app.post("/api/analyze-and-save")
async def analyze_and_save(
    file: UploadFile = File(...),
    user=Depends(current_user),
):
    content = await file.read()

    filename = (
        file.filename
        or "contract"
    )

    result = perform_analysis(
        filename,
        content,
    )

    user_dir = (
        STORAGE_DIR
        / str(user["id"])
    )

    user_dir.mkdir(
        parents=True,
        exist_ok=True,
    )

    safe_name = re.sub(
        r"[^A-Za-z0-9._-]",
        "_",
        filename,
    )

    stored = (
        user_dir
        / f"{secrets.token_hex(8)}_{safe_name}"
    )

    stored.write_bytes(
        content
    )

    timestamp = now_iso()

    connection = db()

    cursor = connection.execute(
        """
        INSERT INTO contracts
        (user_id, filename, stored_path,
         folder, status, favorite,
         risk_score, risk_level,
         created_at, updated_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            user["id"],
            filename,
            str(stored),
            "All Contracts",
            "analyzed",
            0,
            int(
                round(
                    result[
                        "overall_risk_score"
                    ]
                )
            ),
            result[
                "overall_risk_level"
            ],
            timestamp,
            timestamp,
        ),
    )

    contract_id = cursor.lastrowid

    connection.execute(
        """
        INSERT INTO analyses
        (contract_id, result_json, created_at)
        VALUES (?, ?, ?)
        """,
        (
            contract_id,
            __import__(
                "json"
            ).dumps(result),
            timestamp,
        ),
    )

    connection.commit()
    connection.close()

    return {
        "contract_id": contract_id,
        "analysis": result,
    }


@app.post("/api/analyze-many")
async def analyze_many(
    files: List[UploadFile] = File(...),
):
    results = []

    for file in files:
        content = await file.read()

        try:
            result = perform_analysis(
                file.filename or "contract",
                content,
            )

            results.append(
                {
                    "filename": file.filename,
                    "success": True,
                    "analysis": result,
                }
            )

        except HTTPException as exc:
            results.append(
                {
                    "filename": file.filename,
                    "success": False,
                    "error": exc.detail,
                }
            )

    return {
        "results": results
    }


# ============================================================
# CONTRACT LIBRARY
# ============================================================

def serialize_contract(row):
    return {
        "id": row["id"],
        "filename": row["filename"],
        "folder": row["folder"],
        "status": row["status"],
        "favorite": bool(
            row["favorite"]
        ),
        "risk_score": row["risk_score"],
        "risk_level": row["risk_level"],
        "created_at": row["created_at"],
        "updated_at": row["updated_at"],
    }


@app.get("/api/contracts")
def list_contracts(
    user=Depends(current_user),
):
    connection = db()

    rows = connection.execute(
        """
        SELECT * FROM contracts
        WHERE user_id = ?
        ORDER BY created_at DESC
        """,
        (user["id"],),
    ).fetchall()

    connection.close()

    return [
        serialize_contract(row)
        for row in rows
    ]


@app.get("/api/contracts/{contract_id}")
def get_contract(
    contract_id: int,
    user=Depends(current_user),
):
    connection = db()

    row = connection.execute(
        """
        SELECT * FROM contracts
        WHERE id = ? AND user_id = ?
        """,
        (
            contract_id,
            user["id"],
        ),
    ).fetchone()

    if not row:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Contract not found.",
        )

    analysis = connection.execute(
        """
        SELECT result_json
        FROM analyses
        WHERE contract_id = ?
        ORDER BY id DESC
        LIMIT 1
        """,
        (contract_id,),
    ).fetchone()

    connection.close()

    result = serialize_contract(
        row
    )

    if analysis:
        result["analysis"] = __import__(
            "json"
        ).loads(
            analysis["result_json"]
        )

    return result


@app.patch("/api/contracts/{contract_id}")
def update_contract(
    contract_id: int,
    folder: Optional[str] = None,
    favorite: Optional[bool] = None,
    user=Depends(current_user),
):
    connection = db()

    row = connection.execute(
        """
        SELECT * FROM contracts
        WHERE id = ? AND user_id = ?
        """,
        (
            contract_id,
            user["id"],
        ),
    ).fetchone()

    if not row:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Contract not found.",
        )

    new_folder = (
        folder
        if folder is not None
        else row["folder"]
    )

    new_favorite = (
        int(favorite)
        if favorite is not None
        else row["favorite"]
    )

    connection.execute(
        """
        UPDATE contracts
        SET folder = ?, favorite = ?, updated_at = ?
        WHERE id = ?
        """,
        (
            new_folder,
            new_favorite,
            now_iso(),
            contract_id,
        ),
    )

    connection.commit()

    updated = connection.execute(
        "SELECT * FROM contracts WHERE id = ?",
        (contract_id,),
    ).fetchone()

    connection.close()

    return serialize_contract(
        updated
    )


@app.delete("/api/contracts/{contract_id}")
def delete_contract(
    contract_id: int,
    user=Depends(current_user),
):
    connection = db()

    row = connection.execute(
        """
        SELECT * FROM contracts
        WHERE id = ? AND user_id = ?
        """,
        (
            contract_id,
            user["id"],
        ),
    ).fetchone()

    if not row:
        connection.close()

        raise HTTPException(
            status_code=404,
            detail="Contract not found.",
        )

    connection.execute(
        "DELETE FROM analyses WHERE contract_id = ?",
        (contract_id,),
    )

    connection.execute(
        """
        DELETE FROM contracts
        WHERE id = ?
        """,
        (contract_id,),
    )

    connection.commit()
    connection.close()

    try:
        stored_path = row["stored_path"]

        if stored_path:
            Path(stored_path).unlink(
                missing_ok=True
            )

    except Exception:
        pass

    return {
        "message": "Contract deleted successfully."
    }


# ============================================================
# DASHBOARD
# ============================================================

@app.get("/api/dashboard")
def dashboard(
    user=Depends(current_user),
):
    connection = db()

    rows = connection.execute(
        """
        SELECT * FROM contracts
        WHERE user_id = ?
        """,
        (user["id"],),
    ).fetchall()

    connection.close()

    total = len(rows)

    high = sum(
        1
        for row in rows
        if row["risk_score"] >= 70
    )

    medium = sum(
        1
        for row in rows
        if 40 <= row["risk_score"] < 70
    )

    low = sum(
        1
        for row in rows
        if row["risk_score"] < 40
    )

    average = round(
        sum(
            row["risk_score"]
            for row in rows
        ) / total,
        2,
    ) if total else 0

    return {
        "total_contracts": total,
        "average_risk_score": average,
        "high_risk_contracts": high,
        "medium_risk_contracts": medium,
        "low_risk_contracts": low,
        "contracts": [
            serialize_contract(row)
            for row in rows
        ],
    }


# ============================================================
# HEALTH
# ============================================================

@app.get("/health")
def health():
    return {
        "status": "ok",
        "service": "ContractIQ API",
        "model_configured": bool(
            HF_MODEL_ID
        ),
        "hf_token_configured": bool(
            HF_TOKEN
        ),
        "model_id": HF_MODEL_ID,
        "model_classes": len(
            DEFAULT_LABEL_NAMES
        ),
        "ocr_available": False,
        "storage": "Vercel temporary filesystem",
    }


@app.get("/")
def root():
    return {
        "service": "ContractIQ API",
        "status": "online",
        "health": "/health",
    }
