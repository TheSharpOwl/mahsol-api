from pydantic import BaseModel, HttpUrl

class ImageAnalysisRequest(BaseModel):
    image_url: str

class ImageAnalysisResponse(BaseModel):
    analysis: str
