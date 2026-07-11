
from enum import Enum
from pydantic import BaseModel, EmailStr

class UserRole(str, Enum):
    pharmacist = "pharmacist"
    company = "company"
    admin = "admin"


class SignUpRequest(BaseModel):
    email: EmailStr
    password: str
    role: UserRole  