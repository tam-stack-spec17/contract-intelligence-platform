from typing import List

from fastapi import FastAPI, File, UploadFile, HTTPException
from fastapi.middleware.cors import CORSMiddleware


app = FastAPI(
    title="Contract Intelligence API",
    description="Backend API for contract analysis",
    version="1.0.0",
)


# ---------------------------------------------------------
# CORS
# ---------------------------------------------------------

app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ---------------------------------------------------------
# HEALTH CHECK
# ---------------------------------------------------------

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "service": "contract-intelligence-api",
    }


# ---------------------------------------------------------
# CONTRACT ANALYSIS
# ---------------------------------------------------------

@app.post("/api/contracts/analyze")
async def analyze_contract(file: UploadFile = File(...)):

    if not file.filename:
        raise HTTPException(
            status_code=400,
            detail="No file was provided.",
        )

    allowed_extensions = {
        ".pdf",
        ".docx",
    }

    filename = file.filename.lower()

    if not filename.endswith(
        tuple(allowed_extensions)
    ):
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are supported.",
        )

    # Read the uploaded file.
    file_bytes = await file.read()

    if not file_bytes:
        raise HTTPException(
            status_code=400,
            detail="The uploaded file is empty.",
        )

    # -----------------------------------------------------
    # TEMPORARY ANALYSIS RESULT
    # -----------------------------------------------------
    #
    # The team's trained Legal-BERT model and CUAD
    # processed data are not currently present in the
    # repository.
    #
    # This response therefore acts as the API contract
    # for frontend integration.
    #
    # Later, this section will be replaced with the
    # actual NLP/ML inference pipeline.
    #

    result = {
        "contract_name": file.filename,

        "risk_score": 78,

        "risk_level": "HIGH",

        "entities": [
            {
                "label": "PARTY",
                "value": "Company A / Company B",
            },
            {
                "label": "DATE",
                "value": "November 20, 2019",
            },
            {
                "label": "JURISDICTION",
                "value": "Delaware",
            },
            {
                "label": "CONTRACT TYPE",
                "value": "Commercial Agreement",
            },
        ],

        "clauses": [
            {
                "name": "Termination",
                "status": "High Risk",
                "confidence": 0.91,
                "description": (
                    "Termination conditions and notice "
                    "requirements require review."
                ),
            },
            {
                "name": "Confidentiality",
                "status": "Detected",
                "confidence": 0.96,
                "description": (
                    "Confidentiality obligations are "
                    "present in the agreement."
                ),
            },
            {
                "name": "Indemnification",
                "status": "Medium Risk",
                "confidence": 0.87,
                "description": (
                    "Indemnification obligations may "
                    "create additional liability exposure."
                ),
            },
            {
                "name": "Intellectual Property",
                "status": "High Risk",
                "confidence": 0.89,
                "description": (
                    "Ownership and assignment provisions "
                    "should be reviewed carefully."
                ),
            },
            {
                "name": "Auto-Renewal",
                "status": "Review",
                "confidence": 0.82,
                "description": (
                    "Potential renewal obligations "
                    "require manual verification."
                ),
            },
        ],

        "findings": [
            {
                "level": "HIGH",
                "title": "Termination provision",
                "description": (
                    "Review termination conditions "
                    "and notice requirements."
                ),
            },
            {
                "level": "HIGH",
                "title": "Intellectual property ownership",
                "description": (
                    "Review assignment and ownership "
                    "obligations."
                ),
            },
            {
                "level": "MEDIUM",
                "title": "Indemnification obligation",
                "description": (
                    "Potential liability exposure "
                    "should be reviewed."
                ),
            },
        ],
    }

    return result
    