from pydantic import BaseModel
from datetime import datetime
from typing import Optional

class ProductCreate(BaseModel):
    name: str
    description: Optional[str] = None
    illness_id: int
    user_id: str

class ProductUpdate(BaseModel):
    name: Optional[str] = None
    description: Optional[str] = None
    illness_id: Optional[int] = None

class ProductResponse(BaseModel):
    id: str
    name: str
    description: Optional[str]
    illness_id: int
    created_at: datetime
    user_id: str

    model_config = {"from_attributes": True}
