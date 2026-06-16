from pydantic import BaseModel
from datetime import datetime

class IllnessResponse(BaseModel):
    id: int
    name: str
    created_at: datetime

    model_config = {"from_attributes": True}
