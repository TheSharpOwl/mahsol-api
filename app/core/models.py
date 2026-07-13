from enum import Enum

from pydantic import BaseModel, EmailStr


class UserRole(str, Enum):
    farmer = "farmer"
    expert = "expert"
    pharmacist = "pharmacist"
    company = "company"
    admin = "admin"


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class SoilDetails(BaseModel):
    latitude: float
    longitude: float
    soil_type: str | None = None  # WRB reference class, e.g. "Calcisols"
    sand_percent: float | None = None
    silt_percent: float | None = None
    clay_percent: float | None = None
    ph: float | None = None
    organic_carbon: float | None = None  # g/kg
    nitrogen: float | None = None  # g/kg
    cation_exchange_capacity: float | None = None  # cmol(c)/kg
    bulk_density: float | None = None  # kg/dm3
