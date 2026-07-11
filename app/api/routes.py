from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import accounts
from app.core.db import get_db
from app.core.models import SignInRequest, SignUpRequest
from app.core.security import get_current_user

router = APIRouter()


@router.get("/hello", tags=["example"])
def hello() -> dict[str, str]:
    return {"message": "Hello from Mahsol API"}


@router.post("/signup", tags=["auth"], status_code=201)
def sign_up(request: SignUpRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return accounts.sign_up_user(db, request)


@router.post("/signin", tags=["auth"])
def sign_in(request: SignInRequest, db: Session = Depends(get_db)) -> dict[str, str]:
    return accounts.sign_in_user(db, request)


@router.get("/me", tags=["auth"])
def me(current_user: dict = Depends(get_current_user)) -> dict[str, str]:
    return accounts.get_account_info(current_user)
