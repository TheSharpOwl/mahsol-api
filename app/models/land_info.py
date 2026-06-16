import uuid
from datetime import datetime, timezone
from sqlalchemy import String, Float, Text, ForeignKey, DateTime
from sqlalchemy.orm import Mapped, mapped_column, relationship
from app.db.base import Base


class LandInfo(Base):
    __tablename__ = "land_info"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid.uuid4()))
    user_id: Mapped[str] = mapped_column(String(36), ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True)
    latitude: Mapped[float] = mapped_column(Float, nullable=False)
    longitude: Mapped[float] = mapped_column(Float, nullable=False)
    soil_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    crop_type: Mapped[str | None] = mapped_column(String(100), nullable=True)
    additional_notes: Mapped[str | None] = mapped_column(Text, nullable=True)
    smu_id: Mapped[int | None] = mapped_column(nullable=True)
    soil_texture: Mapped[str | None] = mapped_column(String(100), nullable=True)
    sand_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    silt_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    clay_percent: Mapped[float | None] = mapped_column(Float, nullable=True)
    ph: Mapped[float | None] = mapped_column(Float, nullable=True)
    organic_carbon: Mapped[float | None] = mapped_column(Float, nullable=True)
    cation_exchange_capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    bulk_density: Mapped[float | None] = mapped_column(Float, nullable=True)
    electrical_conductivity: Mapped[float | None] = mapped_column(Float, nullable=True)
    gypsum_content: Mapped[float | None] = mapped_column(Float, nullable=True)
    available_water_capacity: Mapped[float | None] = mapped_column(Float, nullable=True)
    soil_components: Mapped[str | None] = mapped_column(Text, nullable=True)  # Store as JSON string

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), default=lambda: datetime.now(timezone.utc)
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        default=lambda: datetime.now(timezone.utc),
        onupdate=lambda: datetime.now(timezone.utc),
    )

    user = relationship("User", back_populates="land_info")
