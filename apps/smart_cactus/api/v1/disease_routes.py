import logging

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from fastapi.responses import JSONResponse

from app.core.dependencies import get_disease_service
from app.schemas.disease_schema import DiseasePredictionResponse
from app.services.disease_service import DiseaseService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/disease", tags=["Disease Prediction"])

_ALLOWED_CONTENT_TYPES = {"image/jpeg", "image/jpg", "image/png", "image/webp"}


@router.post(
    "/predict",
    response_model=DiseasePredictionResponse,
    summary="Predict Tomato Disease",
    description=(
        "Upload a tomato plant leaf image (JPEG / PNG / WebP). "
        "Returns softmax probabilities for all disease classes plus the top prediction."
    ),
    responses={
        200: {"description": "Prediction successful"},
        400: {"description": "Invalid image or unsupported format"},
        503: {"description": "Model not ready"},
    },
)
async def predict_disease(
    request: Request,
    file: UploadFile = File(..., description="Tomato leaf image (JPEG, PNG, WebP)"),
    disease_service: DiseaseService = Depends(get_disease_service),
) -> JSONResponse:
    # Content-type guard (best-effort — clients may omit it)
    if file.content_type and file.content_type.lower() not in _ALLOWED_CONTENT_TYPES:
        raise HTTPException(
            status_code=400,
            detail=(
                f"Unsupported content type '{file.content_type}'. "
                f"Accepted: {', '.join(sorted(_ALLOWED_CONTENT_TYPES))}"
            ),
        )

    image_bytes = await file.read()

    try:
        result = await disease_service.predict_disease(image_bytes)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc))
    except RuntimeError as exc:
        logger.error("Inference runtime error", exc_info=True)
        raise HTTPException(status_code=503, detail=str(exc))
    except Exception:
        logger.error("Unexpected prediction error", exc_info=True)
        raise HTTPException(status_code=500, detail="Internal server error")

    return JSONResponse(content=result)
