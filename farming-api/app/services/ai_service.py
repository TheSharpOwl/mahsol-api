import httpx
import json
import logging
from typing import Optional, Any
from fastapi import UploadFile
from app.core.config import settings

logger = logging.getLogger(__name__)


async def _call_custom_ai_service(payload: dict) -> str:
    """Helper to call the custom AI service."""
    if not settings.AI_SERVICE_URL:
        logger.warning("AI_SERVICE_URL not set, falling back to mock")
        return ""

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                settings.AI_SERVICE_URL,
                json=payload,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response") or data.get("text") or str(data)
    except Exception as e:
        logger.error(f"Custom AI service request failed: {e}")
        return ""


# --- 1. CHAT & WEBSOCKET ---
async def get_chat_response(user_id: str, message: str) -> str:
    """AI response for direct chat/websocket interaction."""
    payload = {
        "user_id": str(user_id),
        "message": message,
        "type": "chat"
    }
    response = await _call_custom_ai_service(payload)
    return response if response else _mock_chat_response(message)


# --- 2. DAILY ADVICE (REPORT PART) ---
async def get_daily_advice(user_id: str, land_info: dict, weather_data: dict) -> str:
    """AI advice for the periodic 24-hour task."""
    prompt = (
        f"Daily Advice Request:\n"
        f"Crop: {land_info.get('crop_type')}, Soil: {land_info.get('soil_type')}\n"
        f"Weather: {weather_data.get('temperature')}C, {weather_data.get('humidity')}% humidity."
    )
    payload = {
        "user_id": str(user_id),
        "message": prompt,
        "type": "daily_advice"
    }
    response = await _call_custom_ai_service(payload)
    return response if response else _mock_daily_advice(land_info, weather_data)


async def _call_custom_ai_service_with_file(user_id: str, file: UploadFile) -> str:
    """Helper to call the custom AI service with an uploaded file."""
    if not settings.AI_SERVICE_URL:
        logger.warning("AI_SERVICE_URL not set, falling back to mock")
        return ""

    try:
        content = await file.read()
        await file.seek(0)

        async with httpx.AsyncClient(timeout=30.0) as client:
            files = {"file": (file.filename, content, file.content_type)}
            data = {
                "user_id": str(user_id),
                "type": "image_analysis"
            }
            response = await client.post(
                settings.AI_SERVICE_URL,
                data=data,
                files=files,
            )
            response.raise_for_status()
            data = response.json()
            return data.get("response") or data.get("text") or str(data)
    except Exception as e:
        logger.error(f"Custom AI service request with file failed: {e}")
        return ""


# --- 3. IMAGE ANALYSIS ---
async def get_image_analysis(user_id: str, file: UploadFile) -> str:
    """AI analysis for a specific crop/land image file."""
    response = await _call_custom_ai_service_with_file(user_id, file)
    return response if response else _mock_image_analysis()


# --- MOCK FALLBACKS ---

def _mock_chat_response(message: str) -> str:
    return f"Mock Chat: I received your message '{message}'. Please configure AI_SERVICE_URL for real AI responses."

def _mock_daily_advice(land_info: dict, weather_data: dict) -> str:
    crop = land_info.get('crop_type', 'crops')
    return f"Mock Advice: Your {crop} look good today. Ensure regular irrigation given the {weather_data.get('temperature')}C temperature."

def _mock_image_analysis() -> str:
    return "Mock Analysis: The image shows a healthy crop with no visible signs of disease."

