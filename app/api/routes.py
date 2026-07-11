import bcrypt
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.db import get_db
from app.core.models import SignUpRequest, User

router = APIRouter()


@router.get("/hello", tags=["example"])
def hello() -> dict[str, str]:
    return {"message": "Hello from Mahsol API"}


@router.post("/signup", tags=["auth"], status_code=201)
def sign_up(request: SignUpRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    existing = db.scalar(select(User).where(User.email == request.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=request.email, hashed_password=hashed, role=request.role)
    db.add(user)
    db.commit()

    return {"message": f"User {user.email} created as {user.role.value}"}
