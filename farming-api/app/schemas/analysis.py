from pydantic import BaseModel, HttpUrl

class ImageAnalysisRequest(BaseModel):
    image_url: str

class PredictionItem(BaseModel):
    disease: str
    confidence: float

class ImageAnalysisResponse(BaseModel):
    analysis: str
