import logging
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from app.models.illness import Illness

logger = logging.getLogger(__name__)

ILLNESS_DATA = {
    0: "Tomato___Bacterial_spot",
    1: "Tomato___Early_blight",
    2: "Tomato___Late_blight",
    3: "Tomato___Leaf_Mold",
    4: "Tomato___Septoria_leaf_spot",
    5: "Tomato___Spider_mites Two-spotted_spider_mite",
    6: "Tomato___Target_Spot",
    7: "Tomato___Tomato_Yellow_Leaf_Curl_Virus",
    8: "Tomato___Tomato_mosaic_virus",
    9: "Tomato___healthy"
}

async def seed_illnesses(db: AsyncSession):
    try:
        for illness_id, name in ILLNESS_DATA.items():
            result = await db.execute(select(Illness).where(Illness.id == illness_id))
            existing = result.scalar_one_or_none()
            if not existing:
                illness = Illness(id=illness_id, name=name)
                db.add(illness)
                logger.info(f"Seeded illness: {name} (ID: {illness_id})")
        await db.commit()
    except Exception as e:
        logger.error(f"Error seeding illnesses: {e}")
        await db.rollback()
