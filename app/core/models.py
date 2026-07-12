
from enum import Enum

from pydantic import BaseModel, EmailStr
from sqlalchemy import String
from sqlalchemy.orm import Mapped, mapped_column

from app.core.db import Base

class UserRole(str, Enum):
    pharmacist = "pharmacist"
    company = "company"
    farmer = "farmer"
    admin = "admin"


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole


class SignInRequest(BaseModel):
    email: EmailStr
    password: str


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    hashed_password: Mapped[str] = mapped_column(String(255))
    role: Mapped[UserRole]
