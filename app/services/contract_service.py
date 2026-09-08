import os
import re

from PyPDF2 import PdfReader
from docx import Document


def extract_pdf_text(file_path: str) -> str:
    text = ""

    reader = PdfReader(file_path)

    for page in reader.pages:
        page_text = page.extract_text()

        if page_text:
            text += page_text + "\n"

    return text


def extract_docx_text(file_path: str) -> str:
    document = Document(file_path)

    paragraphs = []

    for paragraph in document.paragraphs:
        if paragraph.text.strip():
            paragraphs.append(paragraph.text)

    return "\n".join(paragraphs)


def extract_text(file_path: str) -> str:
    extension = os.path.splitext(file_path)[1].lower()

    if extension == ".pdf":
        return extract_pdf_text(file_path)

    if extension == ".docx":
        return extract_docx_text(file_path)

    raise ValueError("Only PDF and DOCX files are supported.")


def detect_clauses(text: str):
    text_lower = text.lower()

    clauses = []

    clause_keywords = {
        "Termination": [
            "termination",
            "terminate",
            "termination of agreement"
        ],
        "Confidentiality": [
            "confidentiality",
            "confidential information",
            "non-disclosure"
        ],
        "Indemnification": [
            "indemnification",
            "indemnify",
            "hold harmless"
        ],
        "Limitation of Liability": [
            "limitation of liability",
            "limited liability",
            "liability shall not exceed"
        ],
        "Governing Law": [
            "governing law",
            "laws of the state",
            "jurisdiction"
        ],
        "Payment": [
            "payment",
            "invoice",
            "fees",
            "payment terms"
        ],
        "Renewal": [
            "renewal",
            "automatically renew",
            "auto-renew"
        ]
    }

    for clause_name, keywords in clause_keywords.items():
        for keyword in keywords:
            if keyword in text_lower:
                clauses.append(clause_name)
                break

    return clauses


def extract_entities(text: str):
    dates = re.findall(
        r"\b(?:\d{1,2}[/-]\d{1,2}[/-]\d{2,4}"
        r"|\d{4}[/-]\d{1,2}[/-]\d{1,2})\b",
        text
    )

    money = re.findall(
        r"(?:\$|₹|€|£)\s?\d[\d,]*(?:\.\d+)?",
        text
    )

    email_addresses = re.findall(
        r"\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}\b",
        text
    )

    return {
        "dates": list(set(dates)),
        "money_amounts": list(set(money)),
        "emails": list(set(email_addresses))
    }


def calculate_risk(text: str, clauses: list):
    text_lower = text.lower()

    risk_flags = []
    risk_score = 0

    high_risk_terms = {
        "unlimited liability": 30,
        "unlimited indemnity": 30,
        "sole discretion": 15,
        "without notice": 15,
        "automatic renewal": 10,
        "auto-renew": 10,
        "penalty": 10,
        "waive": 5,
        "irrevocable": 10,
        "non-compete": 10,
    }

    for term, score in high_risk_terms.items():
        if term in text_lower:
            risk_score += score
            risk_flags.append(
                f"Potentially risky language: '{term}'"
            )

    if "Limitation of Liability" not in clauses:
        risk_score += 15
        risk_flags.append(
            "No clear limitation of liability clause detected."
        )

    if "Termination" not in clauses:
        risk_score += 10
        risk_flags.append(
            "No clear termination clause detected."
        )

    risk_score = min(risk_score, 100)

    if risk_score >= 70:
        risk_level = "HIGH"
    elif risk_score >= 40:
        risk_level = "MEDIUM"
    else:
        risk_level = "LOW"

    return risk_score, risk_level, risk_flags


def analyze_contract(text: str, contract_id: str, filename: str):
    clauses = detect_clauses(text)
    entities = extract_entities(text)

    risk_score, risk_level, risk_flags = calculate_risk(
        text,
        clauses
    )

    summary = (
        f"The contract contains {len(clauses)} detected clause categories "
        f"and {len(risk_flags)} potential risk indicators. "
        f"The calculated risk level is {risk_level}."
    )

    return {
        "contract_id": contract_id,
        "filename": filename,
        "risk_score": risk_score,
        "risk_level": risk_level,
        "entities": entities,
        "clauses": clauses,
        "risk_flags": risk_flags,
        "summary": summary
    }