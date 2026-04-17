import httpx
from typing import Optional, Any
from app.core.config import settings
import logging

logger = logging.getLogger(__name__)


async def fetch_weather(latitude: float, longitude: float) -> Optional[dict[str, Any]]:
    """Fetch current weather data from OpenWeatherMap API."""
    if not settings.OPENWEATHER_API_KEY:
        logger.warning("OPENWEATHER_API_KEY not set, returning mock weather data")
        return _mock_weather(latitude, longitude)

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {
        "lat": latitude,
        "lon": longitude,
        "appid": settings.OPENWEATHER_API_KEY,
        "units": "metric",
    }


    async with httpx.AsyncClient(timeout=10.0) as client:
        response = await client.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        return {
            "temperature": data["main"]["temp"],
            "feels_like": data["main"]["feels_like"],
            "humidity": data["main"]["humidity"],
            "pressure": data["main"]["pressure"],
            "description": data["weather"][0]["description"],
            "wind_speed": data["wind"]["speed"],
            "city": data.get("name"),
            "country": data.get("sys", {}).get("country"),
            "raw": data,
            "note": "called the real APi"
        }


def _mock_weather(latitude: float, longitude: float) -> dict:
    return {
        "temperature": 25.0,
        "feels_like": 26.5,
        "humidity": 65,
        "pressure": 1013,
        "description": "partly cloudy",
        "wind_speed": 3.5,
        "city": "Unknown",
        "country": "Unknown",
        "note": "Called the MOCK API",
        "latitude": latitude,
        "longitude": longitude,
    }
