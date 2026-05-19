from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.land_info import LandInfo
from app.models.user import User
from app.schemas.land_info import LandInfoCreate, LandInfoResponse, LandInfoUpdate
from app.core.security import get_current_user
from app.services.weather_service import fetch_weather
from app.workers.tasks import calculate_soil_profile_task

router = APIRouter(prefix="/land-info", tags=["Land Info"])


@router.post("", response_model=LandInfoResponse, status_code=status.HTTP_201_CREATED)
async def create_or_update_land_info(
    payload: LandInfoCreate,
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Create or update land info for the current user.
    Triggers an asynchronous task to calculate the soil profile.
    """
    result = await db.execute(
        select(LandInfo).where(LandInfo.user_id == current_user.id)
    )
    land = result.scalar_one_or_none()

    if land:
        # Update existing
        land.latitude = payload.latitude
        land.longitude = payload.longitude
        land.soil_type = payload.soil_type
        land.crop_type = payload.crop_type
        land.additional_notes = payload.additional_notes
    else:
        # Create new
        land = LandInfo(
            user_id=current_user.id,
            latitude=payload.latitude,
            longitude=payload.longitude,
            soil_type=payload.soil_type,
            crop_type=payload.crop_type,
            additional_notes=payload.additional_notes,
        )
        db.add(land)

    await db.commit()
    await db.refresh(land)

    # Trigger background task for soil profile calculation
    calculate_soil_profile_task.delay(current_user.id, land.latitude, land.longitude)

    # Fetch weather for the response
    weather = await fetch_weather(land.latitude, land.longitude)
    
    response = LandInfoResponse.model_validate(land)
    response.weather = weather
    return response


@router.get("", response_model=list[LandInfoResponse])
async def list_all_land_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get all land information records for the currently authenticated user.
    """
    result = await db.execute(
        select(LandInfo).where(LandInfo.user_id == current_user.id).order_by(LandInfo.created_at.desc())
    )
    lands = result.scalars().all()
    return [LandInfoResponse.model_validate(l) for l in lands]


@router.get("/me", response_model=LandInfoResponse)
async def get_my_land_info(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    """
    Get the most recent land info for the currently authenticated user.
    """
    result = await db.execute(
        select(LandInfo)
        .where(LandInfo.user_id == current_user.id)
        .order_by(LandInfo.created_at.desc())
        .limit(1)
    )
    land = result.scalar_one_or_none()

    if not land:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Land information not found for this user",
        )

    # Fetch live weather for the response
    weather = await fetch_weather(land.latitude, land.longitude)
    
    response = LandInfoResponse.model_validate(land)
    response.weather = weather
    return response
