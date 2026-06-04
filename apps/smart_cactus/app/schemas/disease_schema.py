from typing import Dict, List, Optional

from pydantic import BaseModel, ConfigDict, Field


class DiseaseTopPrediction(BaseModel):
    disease: str = Field(..., description="Disease class name")
    confidence: float = Field(..., ge=0.0, le=1.0, description="Softmax probability")


class DiseasePrediction(BaseModel):
    disease: str = Field(..., description="Top-ranked disease class")
    confidence: float = Field(..., ge=0.0, le=1.0)
    top_predictions: List[DiseaseTopPrediction] = Field(
        ..., description="Top-K predictions sorted by confidence"
    )
    all_scores: Dict[str, float] = Field(
        ..., description="Softmax probability for every class"
    )


class DiseasePredictionResponse(BaseModel):
    success: bool
    prediction: Optional[DiseasePrediction] = None
    model: str
    error: Optional[str] = None

    model_config = ConfigDict(
        json_schema_extra={
            "example": {
                "success": True,
                "prediction": {
                    "disease": "Tomato___Late_blight",
                    "confidence": 0.94,
                    "top_predictions": [
                        {"disease": "Tomato___Late_blight", "confidence": 0.94},
                        {"disease": "Tomato___Early_blight", "confidence": 0.03},
                        {"disease": "Tomato___healthy", "confidence": 0.02},
                    ],
                    "all_scores": {
                        "Tomato___healthy": 0.02,
                        "Tomato___Early_blight": 0.03,
                        "Tomato___Late_blight": 0.94,
                    },
                },
                "model": "Mahsoul_Ensemble_v3",
                "error": None,
            }
        }
    )
