from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, EmailStr
from sqlalchemy.orm import Session

from src.database import get_db
from src.models.user import User
from src.utils.auth import create_access_token, hash_password, verify_password

router = APIRouter()


class RegisterRequest(BaseModel):
    email: EmailStr
    full_name: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/register", status_code=201)
def register(payload: RegisterRequest, db: Session = Depends(get_db)):
    existing = db.query(User).filter(User.email == payload.email).first()
    if existing:
        raise HTTPException(status_code=400, detail="Email already registered")
    user = User(
        email=payload.email,
        full_name=payload.full_name,
        hashed_password=hash_password(payload.password),
    )
    db.add(user)
    db.commit()
    return {"message": "User registered successfully"}


@router.post("/login", response_model=TokenResponse)
def login(form_data: dict = Depends(), db: Session = Depends(get_db)):
    user = db.query(User).filter(User.email == form_data["username"]).first()
    if not user or not verify_password(form_data["password"], user.hashed_password):
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = create_access_token({"sub": str(user.id), "email": user.email})
    return {"access_token": token}
