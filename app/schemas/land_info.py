from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class LandInfoCreate(BaseModel):
    latitude: float
    longitude: float
    soil_type: Optional[str] = None
    crop_type: Optional[str] = None
    additional_notes: Optional[str] = None


class LandInfoUpdate(BaseModel):
    latitude: Optional[float] = None
    longitude: Optional[float] = None
    soil_type: Optional[str] = None
    crop_type: Optional[str] = None
    additional_notes: Optional[str] = None


class LandInfoResponse(BaseModel):
    id: str
    user_id: str
    latitude: float
    longitude: float
    soil_type: Optional[str]
    crop_type: Optional[str]
    additional_notes: Optional[str]
    created_at: datetime
    updated_at: datetime
    weather: Optional[Any] = None

    model_config = {"from_attributes": True}
