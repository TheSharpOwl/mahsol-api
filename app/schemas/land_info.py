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
    soil_texture: Optional[str] = None
    sand_percent: Optional[float] = None
    silt_percent: Optional[float] = None
    clay_percent: Optional[float] = None
    ph: Optional[float] = None
    organic_carbon: Optional[float] = None
    cation_exchange_capacity: Optional[float] = None
    bulk_density: Optional[float] = None
    electrical_conductivity: Optional[float] = None
    gypsum_content: Optional[float] = None
    available_water_capacity: Optional[float] = None
    soil_components: Optional[str] = None
    created_at: datetime
    updated_at: datetime
    weather: Optional[Any] = None

    model_config = {"from_attributes": True}
