from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.report import Report
from app.models.user import User
from app.schemas.report import ReportResponse
from app.core.security import check_roles
from typing import List
from app.services.weather_service import fetch_weather
from app.services.ai_service import get_daily_advice
from app.models.land_info import LandInfo
from sqlalchemy import select, desc


router = APIRouter(prefix="/reports", tags=["Reports"])


@router.post("/trigger-daily", status_code=status.HTTP_202_ACCEPTED)
async def trigger_daily_reports(current_user: User = Depends(check_roles("farmer"))):
    """
    Manually trigger the 24-hour periodic task for testing.
    This will generate reports for all farmers.
    """
    if current_user.role.value != "admin":
        # Allowing for testing, but in production this should be admin-only
        pass
        
    from app.workers.tasks import generate_daily_reports_task
    generate_daily_reports_task.delay()
    return {"message": "Daily report generation task triggered"}


@router.get("", response_model=List[ReportResponse])
async def list_reports(
    db: AsyncSession = Depends(get_db),
    current_user: User = Depends(check_roles("farmer")),
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
    current_user: User = Depends(check_roles("farmer")),
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
