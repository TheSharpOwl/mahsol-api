import asyncio
import logging
from sqlalchemy import select
from app.workers.celery import celery_app
from app.db.session import async_session_factory, sync_engine
from sqlalchemy.orm import sessionmaker
from app.models.user import User, UserRole
from app.models.land_info import LandInfo
from app.models.report import Report
from app.services.soil_service import soil_service
import json

SessionLocal = sessionmaker(bind=sync_engine)

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
    from app.services.ai_service import get_daily_advice

    async with async_session_factory() as db:
        result = await db.execute(
            select(LandInfo).where(LandInfo.user_id == farmer.id)
        )
        land = result.scalar_one_or_none()

    if land:
        land_data = {
            "latitude": land.latitude,
            "longitude": land.longitude,
            "soil_type": land.soil_type,
            "crop_type": land.crop_type,
            "additional_notes": land.additional_notes,
            "soil_texture": land.soil_texture,
            "sand_percent": land.sand_percent,
            "silt_percent": land.silt_percent,
            "clay_percent": land.clay_percent,
            "ph": land.ph,
            "organic_carbon": land.organic_carbon,
            "cation_exchange_capacity": land.cation_exchange_capacity,
            "bulk_density": land.bulk_density,
            "electrical_conductivity": land.electrical_conductivity,
            "gypsum_content": land.gypsum_content,
            "available_water_capacity": land.available_water_capacity,
        }
        weather_data = await fetch_weather(land.latitude, land.longitude)
    else:
        logger.info(f"Farmer {farmer.id} has no land info, generating report without it")
        land_data = None
        weather_data = {}

    report_text = await get_daily_advice(farmer.id, land_data, weather_data or {})

    async with async_session_factory() as db:
        report = Report(
            user_id=farmer.id,
            weather_data=weather_data,
            warning="Daily Advice",
            report_text=report_text,
        )
        db.add(report)
        await db.commit()

    logger.info(f"Report generated for farmer {farmer.id}")


@celery_app.task(name="app.workers.tasks.calculate_soil_profile_task")
def calculate_soil_profile_task(user_id: str, lat: float, lon: float):
    logger.info(f"Starting soil profile calculation for user {user_id}")
    try:
        with SessionLocal() as db:
            # Check user role - only run for farmers
            user = db.query(User).filter(User.id == user_id).first()
            if not user or user.role != UserRole.farmer:
                logger.info(f"User {user_id} is not a farmer, skipping soil profile calculation")
                return

            # Check if LandInfo already exists
            existing = db.query(LandInfo).filter(LandInfo.user_id == user_id).first()
            if existing:
                logger.info(f"LandInfo already exists for user {user_id}, skipping")
                return

            # Calculate profile using soil_service
            profile_data = soil_service.get_agriculture_soil_profile(lat, lon)
            
            if "error" in profile_data:
                logger.error(f"Soil profile error for user {user_id}: {profile_data['error']}")
                return

            profile = profile_data["profile"]
            
            land = LandInfo(
                user_id=user_id,
                latitude=lat,
                longitude=lon,
                smu_id=profile_data["smu_id"],
                soil_texture=profile_data["soil_texture"],
                sand_percent=profile.get("sand"),
                silt_percent=profile.get("silt"),
                clay_percent=profile.get("clay"),
                ph=profile.get("ph_water"),
                organic_carbon=profile.get("org_carbon"),
                cation_exchange_capacity=profile.get("cec_soil"),
                bulk_density=profile.get("bulk"),
                electrical_conductivity=profile.get("elec_cond"),
                gypsum_content=profile.get("gypsum"),
                available_water_capacity=profile.get("awc"),
                soil_components=json.dumps(profile_data["components"])
            )
            db.add(land)
            db.commit()
            logger.info(f"Soil profile calculation completed for user {user_id}")
    except Exception as exc:
        logger.error(f"Soil profile calculation failed for user {user_id}: {exc}")


def _notify_farmer(user_id: str, warning: str):
    logger.info(f"[NOTIFICATION] Farmer {user_id}: {warning}")
