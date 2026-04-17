from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.land_info import LandInfo
from app.models.user import User
from app.schemas.land_info import LandInfoCreate, LandInfoUpdate, LandInfoResponse
from app.core.security import get_current_user
from app.services.weather_service import fetch_weather

router = APIRouter(prefix="/land-info", tags=["Land Info"])


@router.post("", response_model=LandInfoResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_land_info(
    payload: LandInfoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(LandInfo).where(LandInfo.user_id == current_user.id))
    existing = result.scalar_one_or_none()

    if existing:
        for field, value in payload.model_dump(exclude_none=True).items():
            setattr(existing, field, value)
        await db.commit()
        await db.refresh(existing)
        land = existing
    else:
        land = LandInfo(user_id=current_user.id, **payload.model_dump())
        db.add(land)
        await db.commit()
        await db.refresh(land)

    weather = await fetch_weather(land.latitude, land.longitude)
    response = LandInfoResponse.model_validate(land)
    response.weather = weather
    return response


@router.get("/me", response_model=LandInfoResponse)
async def get_my_land_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(select(LandInfo).where(LandInfo.user_id == current_user.id))
    land = result.scalar_one_or_none()

    if not land:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Land info not found")

    weather = await fetch_weather(land.latitude, land.longitude)
    response = LandInfoResponse.model_validate(land)
    response.weather = weather
    return response
