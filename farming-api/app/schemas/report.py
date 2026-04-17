from pydantic import BaseModel
from datetime import datetime
from typing import Optional, Any


class ReportResponse(BaseModel):
    id: str
    user_id: str
    weather_data: Optional[Any]
    warning: Optional[str]
    report_text: Optional[str]
    created_at: datetime

    model_config = {"from_attributes": True}
