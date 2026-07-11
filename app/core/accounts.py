import bcrypt
from fastapi import HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.core.models import SignInRequest, SignUpRequest, User
from app.core.security import create_access_token


def sign_up_user(db: Session, request: SignUpRequest) -> dict[str, str]:
    existing = db.scalar(select(User).where(User.email == request.email))
    if existing is not None:
        raise HTTPException(status_code=409, detail="Email already registered")

    hashed = bcrypt.hashpw(request.password.encode(), bcrypt.gensalt()).decode()
    user = User(email=request.email, hashed_password=hashed, role=request.role)
    db.add(user)
    db.commit()

    return {"message": f"User {user.email} created as {user.role.value}"}


def sign_in_user(db: Session, request: SignInRequest) -> dict[str, str]:
    user = db.scalar(select(User).where(User.email == request.email))
    # Same error for unknown email and wrong password, so the endpoint
    # doesn't reveal which emails are registered
    if user is None or not bcrypt.checkpw(
        request.password.encode(), user.hashed_password.encode()
    ):
        raise HTTPException(status_code=401, detail="Invalid email or password")

    token = create_access_token(user.email, user.role.value)
    return {
        "access_token": token,
        "token_type": "bearer",
        "email": user.email,
        "role": user.role.value,
    }


def get_account_info(current_user: dict) -> dict[str, str]:
    return {"email": current_user["sub"], "role": current_user["role"]}
