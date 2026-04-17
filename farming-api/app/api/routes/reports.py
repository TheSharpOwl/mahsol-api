from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportResponse
from app.core.security import get_current_user
from typing import List
from app.services.weather_service import fetch_weather
from app.services.ai_service import get_ai_advice
from app.models.land_info import LandInfo
from sqlalchemy import select, desc


router = APIRouter(prefix="/reports", tags=["Reports"])


async def get_latest_land_info(user_id: str, db: AsyncSession):
    result = await db.execute(
        select(LandInfo)
        .where(LandInfo.user_id == user_id)
        .order_by(desc(LandInfo.created_at))
        .limit(1)
    )
    return result.scalar_one_or_none()

@router.get("/assistant/insights")
async def assistant_insights(
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    land = await get_latest_land_info(current_user.id, db)

    if not land:
        raise HTTPException(status_code=404, detail="No land info found")

    weather = await fetch_weather(land.latitude, land.longitude)

    ai_response = await get_ai_advice(land, weather)

    return {
        "land": {
            "soil_type": land.soil_type,
            "crop_type": land.crop_type,
        },
        "weather": weather,
        "advice": ai_response,
    }

@router.get("", response_model=List[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
    )
    reports = result.scalars().all()
    return [ReportResponse.model_validate(r) for r in reports]


@router.get("/latest", response_model=ReportResponse)
async def get_latest_report(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(get_current_user),
):
    result = await db.execute(
        select(Report)
        .where(Report.user_id == current_user.id)
        .order_by(Report.created_at.desc())
        .limit(1)
    )
    report = result.scalar_one_or_none()

    if not report:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="No reports found. Reports are generated daily.",
        )

    return ReportResponse.model_validate(report)
