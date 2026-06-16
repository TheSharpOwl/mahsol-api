from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.db.session import get_db
from app.models.illness import Illness
from app.schemas.illness import IllnessResponse

router = APIRouter(prefix="/illnesses", tags=["Illnesses"])

@router.get("", response_model=list[IllnessResponse])
async def list_illnesses(db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(Illness))
    return result.scalars().all()
