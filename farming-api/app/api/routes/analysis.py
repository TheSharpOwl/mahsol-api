from fastapi import APIRouter, Depends, HTTPException, File, UploadFile
from app.core.security import get_current_user
from app.models.user import User
from app.schemas.analysis import ImageAnalysisResponse
from app.services.ai_service import get_image_analysis

router = APIRouter(prefix="/analysis", tags=["Analysis"])

@router.post("/image", response_model=ImageAnalysisResponse)
async def analyze_image(
    file: UploadFile = File(...),
    current_user: User = Depends(get_current_user)
):
    """
    Takes an image file and returns analysis from the custom AI service.
    """
    if not file.content_type.startswith("image/"):
        raise HTTPException(status_code=400, detail="Uploaded file is not an image.")

    analysis_text = await get_image_analysis(current_user.id, file)
    
    if not analysis_text:
        raise HTTPException(status_code=500, detail="AI analysis failed")
        
    return ImageAnalysisResponse(analysis=analysis_text)
