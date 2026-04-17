import httpx
import json
import logging
from typing import Optional, Any
from app.core.config import settings

logger = logging.getLogger(__name__)


async def get_chat_response(user_message: str, conversation_history: list[dict] | None = None) -> str:
    """Get AI response for chat message. Falls back to mock if no API key."""
    if not settings.OPENAI_API_KEY:
        return _mock_chat_response(user_message)

    messages = conversation_history or []
    messages.append({"role": "user", "content": user_message})

    system_prompt = (
        "You are an expert agricultural assistant helping farmers diagnose crop diseases, "
        "manage their land, and improve yields. Provide practical, science-based advice. "
        "When the user shares an image, analyze it for signs of crop disease, pest damage, or nutrient deficiencies. "
        "Always ask clarifying questions when needed and provide step-by-step actionable recommendations."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [{"role": "system", "content": system_prompt}] + messages,
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
    except Exception as e:
        logger.error(f"AI chat request failed: {e}")
        return _mock_chat_response(user_message)


async def generate_daily_report(
    land_info: dict[str, Any],
    weather_data: dict[str, Any],
) -> dict[str, str]:
    """Generate a daily farming report with warning and summary."""
    if not settings.OPENAI_API_KEY:
        return _mock_daily_report(land_info, weather_data)

    prompt = (
        f"Generate a daily farming report for the following farm:\n\n"
        f"Land Info:\n{json.dumps(land_info, indent=2)}\n\n"
        f"Current Weather:\n{json.dumps(weather_data, indent=2)}\n\n"
        f"Please provide:\n"
        f"1. A concise WARNING about any risks (disease, weather, pests) — 1-2 sentences\n"
        f"2. A REPORT with actionable recommendations for today — 3-5 sentences\n\n"
        f"Respond as JSON with keys 'warning' and 'report_text'."
    )

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": "You are an expert agricultural AI assistant. Respond only in valid JSON."},
                        {"role": "user", "content": prompt},
                    ],
                    "max_tokens": 400,
                    "temperature": 0.5,
                    "response_format": {"type": "json_object"},
                },
            )
            response.raise_for_status()
            data = response.json()
            result = json.loads(data["choices"][0]["message"]["content"])
            return {
                "warning": result.get("warning", ""),
                "report_text": result.get("report_text", ""),
            }
    except Exception as e:
        logger.error(f"AI report generation failed: {e}")
        return _mock_daily_report(land_info, weather_data)


def _mock_chat_response(user_message: str) -> str:
    if "disease" in user_message.lower() or "sick" in user_message.lower():
        return (
            "Based on your description, your crop may be showing signs of a fungal infection. "
            "Look for yellowing leaves, spots, or unusual growth patterns. "
            "I recommend applying a copper-based fungicide and ensuring proper drainage. "
            "Could you share an image for a more accurate diagnosis?"
        )
    if "weather" in user_message.lower():
        return (
            "Current weather conditions are important for your crops. "
            "High humidity can promote fungal diseases, while drought stress can weaken plants. "
            "Make sure to monitor soil moisture and adjust irrigation accordingly."
        )
    return (
        "Thank you for your question! As your farming assistant, I'm here to help with crop health, "
        "disease diagnosis, weather adaptation, and best farming practices. "
        "Could you provide more details about your current situation so I can give you specific advice? "
        "(Note: Set OPENAI_API_KEY in your .env for real AI responses.)"
    )


def _mock_daily_report(land_info: dict, weather_data: dict) -> dict[str, str]:
    temp = weather_data.get("temperature", 25)
    humidity = weather_data.get("humidity", 60)
    crop = land_info.get("crop_type", "your crops")

    warning = (
        f"High humidity ({humidity}%) may increase risk of fungal disease for {crop}. "
        f"Monitor plants closely and ensure good air circulation."
        if humidity > 70
        else f"Weather conditions look favorable for {crop} today."
    )

    report_text = (
        f"Today's temperature is {temp}°C with {humidity}% humidity. "
        f"Recommended actions: check soil moisture levels, inspect {crop} for early signs of pest or disease, "
        f"and ensure drainage is functioning properly. "
        f"If irrigating, do so in the early morning to reduce fungal risk. "
        f"Set OPENAI_API_KEY in your .env for AI-generated personalized reports."
    )

    return {"warning": warning, "report_text": report_text}


async def get_ai_advice(land, weather) -> str:
    """Get AI farming advice based on land + weather."""

    if not settings.OPENAI_API_KEY:
        return _mock_ai_advice(land, weather)

    system_prompt = (
        "You are an expert agricultural assistant helping farmers optimize crop yield, "
        "prevent diseases, and manage resources efficiently. "
        "Provide clear, practical, and actionable advice tailored to the farmer's land and current weather conditions. "
        "Focus on irrigation, fertilization, disease prevention, and weather adaptation. "
        "Keep the response structured and easy to follow."
    )

    user_prompt = f"""
    Here is the farmer's land information:

    - Soil type: {land.soil_type or "Unknown"}
    - Crop type: {land.crop_type or "Unknown"}
    - Additional notes: {land.additional_notes or "None"}
    - Location: latitude {land.latitude}, longitude {land.longitude}

    Current weather conditions:
    - Temperature: {weather.get("temperature", "Unknown")}°C
    - Wind speed: {weather.get("windspeed", "Unknown")} km/h
    - Weather code: {weather.get("weathercode", "Unknown")}

    Based on this data:
    1. Assess current risks (disease, drought, pests, etc.)
    2. Recommend irrigation strategy
    3. Suggest fertilization or soil improvements
    4. Provide preventive actions for the next few days

    Keep it concise but practical.
    """

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                "https://api.openai.com/v1/chat/completions",
                headers={
                    "Authorization": f"Bearer {settings.OPENAI_API_KEY}",
                    "Content-Type": "application/json",
                },
                json={
                    "model": "gpt-4o-mini",
                    "messages": [
                        {"role": "system", "content": system_prompt},
                        {"role": "user", "content": user_prompt},
                    ],
                    "max_tokens": 500,
                    "temperature": 0.7,
                },
            )

            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]

    except Exception as e:
        logger.error(f"AI advice request failed: {e}")
        return _mock_ai_advice(land, weather)


def _mock_ai_advice(land, weather) -> str:
    """Fallback farming advice when AI is unavailable."""

    temp = weather.get("temperature")
    crop = (land.crop_type or "").lower()
    soil = (land.soil_type or "").lower()

    if temp and temp > 30:
        return (
            "High temperatures detected. Your crops may experience heat stress. "
            "Increase irrigation frequency, preferably early morning or late evening to reduce evaporation. "
            "Consider mulching to retain soil moisture and protect roots."
        )

    if "clay" in soil:
        return (
            "Clay soil retains water well but can cause poor drainage. "
            "Avoid overwatering and consider adding organic matter to improve aeration and root health."
        )

    if "wheat" in crop:
        return (
            "Wheat crops benefit from moderate watering and nitrogen-rich fertilization. "
            "Monitor for fungal diseases, especially in humid conditions, and ensure proper spacing for airflow."
        )

    return (
        "Based on your land and current weather, maintain balanced irrigation and monitor crop health closely. "
        "Check for early signs of pests or disease and adjust care depending on temperature and soil conditions. "
        "Adding organic compost can improve long-term soil fertility."
    )