from pydantic import BaseModel, EmailStr
from typing import List, Optional


class UserRegister(BaseModel):
    username: str
    email: EmailStr
    password: str


class UserLogin(BaseModel):
    username: str
    password: str


class Token(BaseModel):
    access_token: str
    token_type: str


class UserResponse(BaseModel):
    username: str
    email: EmailStr


class ContractUploadResponse(BaseModel):
    contract_id: str
    filename: str
    message: str


class AnalysisResponse(BaseModel):
    contract_id: str
    filename: str
    risk_score: int
    risk_level: str
    entities: dict
    clauses: List[str]
    risk_flags: List[str]
    summary: str