from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from app.core import accounts, soil
from app.core.db import get_db
from app.core.models import SignInRequest, SignUpRequest, SoilDetails
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


@router.get("/soil/lookup", tags=["soil"])
async def soil_lookup(
    latitude: float,
    longitude: float,
    current_user: dict = Depends(get_current_user),
) -> SoilDetails:
    return await soil.fetch_soil_details(latitude, longitude)


@router.post("/soil", tags=["soil"], status_code=201)
def save_soil(
    details: SoilDetails,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> dict[str, str]:
    return soil.save_soil_details(db, current_user["sub"], details)
