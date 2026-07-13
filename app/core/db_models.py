from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base
from app.core.models import UserRole


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole]


class SoilInfo(Base):
    __tablename__ = "soil_info"

    id: Mapped[int] = mapped_column(primary_key=True)
    # One soil profile per account, updated in place; joined to users.id
    # in queries rather than enforced with a foreign key
    user_id: Mapped[int] = mapped_column(unique=True)
    latitude: Mapped[float]
    longitude: Mapped[float]
    soil_type: Mapped[str | None] = mapped_column(String(100))
    sand_percent: Mapped[float | None]
    silt_percent: Mapped[float | None]
    clay_percent: Mapped[float | None]
    ph: Mapped[float | None]
    organic_carbon: Mapped[float | None]
    nitrogen: Mapped[float | None]
    cation_exchange_capacity: Mapped[float | None]
    bulk_density: Mapped[float | None]
