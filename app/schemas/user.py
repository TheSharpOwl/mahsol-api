from pydantic import BaseModel, EmailStr, field_validator
from datetime import datetime
from app.models.user import UserRole


class UserSignupRequest(BaseModel):
    username: str
    email: EmailStr | None = None
    password: str
    role: UserRole = UserRole.farmer
    latitude: float
    longitude: float

    @field_validator("role")
    @classmethod
    def role_must_be_valid(cls, v):
        if v == UserRole.admin:
            raise ValueError("Cannot self-register as admin")
        return v


class UserLoginRequest(BaseModel):
    username: str
    password: str


class UserResponse(BaseModel):
    id: str
    username: str
    role: UserRole
    created_at: datetime

    model_config = {"from_attributes": True}


class TokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"
    user: UserResponse
