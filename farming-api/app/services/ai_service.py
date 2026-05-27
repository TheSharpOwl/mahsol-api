import httpx
import logging
from typing import Optional
from fastapi import UploadFile
from app.core.config import settings

logger = logging.getLogger(__name__)


def _get_mock_chat_data(message: str) -> dict:
    msg_lower = message.lower()
    if "expert" in msg_lower:
        return {"answer": "I don't know the answer. Let me connect you with an expert.", "action": "call_expert", "success": True}
    elif "product" in msg_lower:
        return {"answer": "It seems you have Late Blight. Here are some recommended products.", "action": "ask_for_product", "illness_id": 2, "success": True}
        
    return {"answer": _mock_chat_response(message), "action": "message", "success": True}


# --- 1. CHAT & WEBSOCKET ---
async def get_chat_response(user_id: str, message: str) -> dict:
    """AI response for direct chat/websocket interaction."""
    if not settings.AI_CHAT_URL:
        logger.warning("AI_CHAT_URL not set, falling back to mock")
        return _get_mock_chat_data(message)

    payload = {
        "user_id": str(user_id),
        "message": message,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.AI_CHAT_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            
            action = data.get("action", "message")
            illness_id = data.get("illness_id")
            
            logger.info(f"AI response parsed - Action: {action}, Illness ID: {illness_id}")
            
            return {
                "answer": data.get("answer", data.get("response", data.get("text", str(data)))),
                "action": action,
                "illness_id": illness_id,
                "success": data.get("success", True)
            }
    except Exception as e:
        logger.error(f"AI chat service request failed: {e}")
        return _get_mock_chat_data(message)


# --- 2. DAILY ADVICE (REPORT PART) ---
async def get_daily_advice(user_id: str, land_info: Optional[dict], weather_data: dict) -> str:
    """AI advice for the periodic 24-hour task."""
    if not settings.AI_ADVICE_URL:
        logger.warning("AI_ADVICE_URL not set, falling back to mock")
        return _mock_daily_advice(land_info or {}, weather_data)

    # Build prompt, handling missing land info gracefully
    if not land_info:
        prompt = (
            "Land information is not available for this user.\n"
            f"Weather: {weather_data.get('temperature')}C, "
            f"{weather_data.get('humidity')}% humidity.\n"
            "Please provide general daily farming advice."
        )
    else:
        prompt = (
            f"Daily Advice Request:\n"
            f"Crop: {land_info.get('crop_type')}, Soil: {land_info.get('soil_type')}\n"
            f"Weather: {weather_data.get('temperature')}C, "
            f"{weather_data.get('humidity')}% humidity."
        )

    payload = {
        "message": prompt,
    }

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(settings.AI_ADVICE_URL, json=payload)
            response.raise_for_status()
            data = response.json()
            return data.get("response") or data.get("text") or str(data)
    except Exception as e:
        logger.error(f"AI advice service request failed: {e}")
        return _mock_daily_advice(land_info or {}, weather_data)


# --- 3. IMAGE ANALYSIS ---
async def _call_custom_ai_service_with_file(file: UploadFile) -> dict:
    """Helper to call the custom AI image service with only the uploaded file."""
    if not settings.AI_IMAGE_URL:
        logger.warning("AI_IMAGE_URL not set, falling back to mock")
        return {}

    try:
        content = await file.read()
        await file.seek(0)

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (file.filename, content, file.content_type)}
            response = await client.post(
                settings.AI_IMAGE_URL,
                files=files,
            )
            response.raise_for_status()
            return response.json()
    except Exception as e:
        logger.error(f"AI image service request with file failed: {e}")
        return {}


async def get_image_analysis(user_id: str, file: UploadFile) -> str:
    """AI analysis for a specific crop/land image file."""
    data = await _call_custom_ai_service_with_file(file)
    
    if not data or not data.get("success") or "prediction" not in data:
        return _mock_image_analysis()

    prediction = data["prediction"]
    disease = prediction.get("disease", "Unknown")
    confidence = prediction.get("confidence", 0.0)

    message = f"Detected {disease} with {confidence * 100:.1f}% confidence."
    return message


# --- MOCK FALLBACKS ---

def _mock_chat_response(message: str) -> str:
    return f"Mock Chat: I received your message '{message}'. Please configure AI_CHAT_URL for real AI responses."

def _mock_daily_advice(land_info: dict, weather_data: dict) -> str:
    crop = land_info.get('crop_type', 'crops')
    return f"Mock Advice: Your {crop} look good today. Ensure regular irrigation given the {weather_data.get('temperature')}C temperature."

def _mock_image_analysis() -> str:
    return "Mock Analysis: The image shows a healthy crop with no visible signs of disease."

