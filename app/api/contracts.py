import os
import uuid
from app.services.ml_service import analyze_with_ml
from fastapi import APIRouter, UploadFile, File, HTTPException, Depends
from sqlalchemy.orm import Session

from app.api.auth import get_current_user
from app.db import get_db
from app.models.database import Contract
from app.services.contract_service import extract_text, analyze_contract


router = APIRouter(prefix="/api/contracts", tags=["Contracts"])

UPLOAD_DIR = "uploads"
MAX_FILE_SIZE = 10 * 1024 * 1024  # 10 MB

os.makedirs(UPLOAD_DIR, exist_ok=True)


@router.post("/upload")
async def upload_contract(
    file: UploadFile = File(...),
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    allowed_extensions = [".pdf", ".docx"]

    extension = os.path.splitext(file.filename)[1].lower()

    if extension not in allowed_extensions:
        raise HTTPException(
            status_code=400,
            detail="Only PDF and DOCX files are allowed."
        )

    contract_id = str(uuid.uuid4())

    safe_filename = f"{contract_id}{extension}"
    file_path = os.path.join(UPLOAD_DIR, safe_filename)

    total_size = 0

    try:
        with open(file_path, "wb") as buffer:
            while True:
                chunk = await file.read(1024 * 1024)

                if not chunk:
                    break

                total_size += len(chunk)

                if total_size > MAX_FILE_SIZE:
                    raise HTTPException(
                        status_code=413,
                        detail="File size must not exceed 10 MB."
                    )

                buffer.write(chunk)

    except HTTPException:
        if os.path.exists(file_path):
            os.remove(file_path)
        raise

    try:
        text = extract_text(file_path)

    except Exception as e:
        if os.path.exists(file_path):
            os.remove(file_path)

        raise HTTPException(
            status_code=400,
            detail=f"Could not read document: {str(e)}"
        )

        analysis = analyze_contract(text=text, contract_id=contract_id, filename=file.filename)
    ml_analysis = analyze_with_ml(text)
    

    new_contract = Contract(
        contract_id=contract_id,
        filename=file.filename,
        file_path=file_path,
        text=text,
        risk_score=analysis["risk_score"],
        risk_level=analysis["risk_level"],
        owner_id=current_user.id
    )

    db.add(new_contract)
    db.commit()
    db.refresh(new_contract)

    return {
    "message": "Contract uploaded and analyzed successfully",
    "contract_id": contract_id,
    "filename": file.filename,
    "risk_score": analysis["risk_score"],
    "risk_level": analysis["risk_level"],
    "ml_analysis": ml_analysis
}


@router.get("/")
def list_contracts(
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contracts = db.query(Contract).filter(
        Contract.owner_id == current_user.id
    ).all()

    results = []

    for contract in contracts:
        results.append({
            "contract_id": contract.contract_id,
            "filename": contract.filename,
            "risk_score": contract.risk_score,
            "risk_level": contract.risk_level
        })

    return {"contracts": results}


@router.get("/{contract_id}")
def get_contract(
    contract_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(
        Contract.contract_id == contract_id
    ).first()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found"
        )

    if contract.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this contract"
        )

    return {
        "contract_id": contract.contract_id,
        "filename": contract.filename,
        "text": contract.text
    }


@router.get("/{contract_id}/analysis")
def get_analysis(
    contract_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(
        Contract.contract_id == contract_id
    ).first()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found"
        )

    if contract.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this contract"
        )

    analysis = analyze_contract(
        text=contract.text,
        contract_id=contract.contract_id,
        filename=contract.filename
    )

    return analysis


@router.get("/{contract_id}/risk")
def get_risk(
    contract_id: str,
    current_user=Depends(get_current_user),
    db: Session = Depends(get_db)
):
    contract = db.query(Contract).filter(
        Contract.contract_id == contract_id
    ).first()

    if not contract:
        raise HTTPException(
            status_code=404,
            detail="Contract not found"
        )

    if contract.owner_id != current_user.id:
        raise HTTPException(
            status_code=403,
            detail="You do not have access to this contract"
        )

    analysis = analyze_contract(
        text=contract.text,
        contract_id=contract.contract_id,
        filename=contract.filename
    )

    return {
        "contract_id": contract.contract_id,
        "risk_score": contract.risk_score,
        "risk_level": contract.risk_level,
        "risk_flags": analysis["risk_flags"]
    }