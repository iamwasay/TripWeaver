from datetime import datetime
from app.config import get_settings
from app.services.api_client import fetch_json
from app.utils.logger import logger
from app.utils.locations import get_city_name

settings = get_settings()


async def get_weather_context(destination: str) -> dict:
    if not settings.weather_api_key:
        logger.warning("No WEATHER_API_KEY found. Using mock weather data.")
        return {
            "condition": "Seasonal (Mocked)",
            "temperature_c": 12.0,
            "source": "Mock Data",
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    # Translate IATA code (e.g., DXB) to City Name (e.g., Dubai)
    city_query = get_city_name(destination)

    url = "https://api.openweathermap.org/data/2.5/weather"
    params = {"q": city_query, "appid": settings.weather_api_key, "units": "metric"}

    logger.info(f"Fetching weather for {city_query}")
    try:
        data = await fetch_json(url, params=params)
        return {
            "condition": data["weather"][0]["description"],
            "temperature_c": data["main"]["temp"],
            "source": "OpenWeatherMap",
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    except Exception as e:
        logger.error(f"Weather API failed: {str(e)}")
        return {
            "condition": "Unknown",
            "temperature_c": None,
            "source": "Error Fallback",
            "retrieved_at": datetime.utcnow().isoformat(),
            "error": str(e),
        }
