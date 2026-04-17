import asyncio
import logging
from sqlalchemy import select
from app.workers.celery import celery_app
from app.db.session import async_session_factory
from app.models.user import User, UserRole
from app.models.land_info import LandInfo
from app.models.report import Report

logger = logging.getLogger(__name__)


def run_async(coro):
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(coro)
    finally:
        loop.close()


@celery_app.task(name="app.workers.tasks.generate_daily_reports_task", bind=True, max_retries=3)
def generate_daily_reports_task(self):
    logger.info("Starting daily report generation task")
    try:
        run_async(_generate_all_farmer_reports())
        logger.info("Daily report generation completed")
    except Exception as exc:
        logger.error(f"Daily report generation failed: {exc}")
        raise self.retry(exc=exc, countdown=60 * 5)


async def _generate_all_farmer_reports():
    from app.services.weather_service import fetch_weather
    from app.services.ai_service import generate_daily_report

    async with async_session_factory() as db:
        result = await db.execute(
            select(User).where(User.role == UserRole.farmer)
        )
        farmers = result.scalars().all()

    logger.info(f"Generating reports for {len(farmers)} farmers")

    for farmer in farmers:
        try:
            await _generate_farmer_report(farmer)
        except Exception as e:
            logger.error(f"Failed to generate report for farmer {farmer.id}: {e}")


async def _generate_farmer_report(farmer: User):
    from app.services.weather_service import fetch_weather
    from app.services.ai_service import generate_daily_report

    async with async_session_factory() as db:
        result = await db.execute(
            select(LandInfo).where(LandInfo.user_id == farmer.id)
        )
        land = result.scalar_one_or_none()

    if not land:
        logger.info(f"Farmer {farmer.id} has no land info, skipping report")
        return

    land_data = {
        "crop_type": land.crop_type,
        "soil_type": land.soil_type,
        "additional_notes": land.additional_notes,
        "latitude": land.latitude,
        "longitude": land.longitude,
    }

    weather_data = await fetch_weather(land.latitude, land.longitude)
    report_content = await generate_daily_report(land_data, weather_data or {})

    async with async_session_factory() as db:
        report = Report(
            user_id=farmer.id,
            weather_data=weather_data,
            warning=report_content.get("warning"),
            report_text=report_content.get("report_text"),
        )
        db.add(report)
        await db.commit()

    _notify_farmer(farmer.id, report_content.get("warning", ""))
    logger.info(f"Report generated for farmer {farmer.id}")


def _notify_farmer(user_id: str, warning: str):
    logger.info(f"[NOTIFICATION] Farmer {user_id}: {warning}")
