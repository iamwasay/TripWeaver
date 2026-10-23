from datetime import datetime
from app.config import get_settings
from app.services.api_client import fetch_json
from app.utils.logger import logger
from app.utils.locations import get_city_name

settings = get_settings()


async def get_weather_forecast(
    destination: str, start_date_str: str, end_date_str: str
) -> dict:
    if not settings.weather_api_key:
        logger.warning("No WEATHER_API_KEY found. Using mock weather data.")
        return {
            "forecasts": [],
            "current_context": {"temp_c": 22.0, "condition": "Mock Clear Sky"},
            "source": "Mock Data",
            "message": "Mock weather context.",
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    city_query = get_city_name(destination)
    logger.info(f"Fetching weather forecast via OpenWeatherMap for {city_query}")

    try:
        # Step 1: Try to get the 5-day forecast
        url = "https://api.openweathermap.org/data/2.5/forecast"
        params = {"q": city_query, "appid": settings.weather_api_key, "units": "metric"}
        data = await fetch_json(url, params=params)

        if "list" not in data:
            raise ValueError("Invalid response format from weather API.")

        start_date = datetime.strptime(start_date_str, "%Y-%m-%d").date()
        end_date = datetime.strptime(end_date_str, "%Y-%m-%d").date()

        daily_forecasts = {}

        # The API returns 3-hour increments. We'll grab the 12:00 PM reading for each day.
        for item in data["list"]:
            dt_txt = item.get("dt_txt", "")
            if not dt_txt:
                continue

            date_str, time_str = dt_txt.split(" ")
            current_date = datetime.strptime(date_str, "%Y-%m-%d").date()

            if start_date <= current_date <= end_date:
                if time_str.startswith("12:00") and current_date not in daily_forecasts:
                    daily_forecasts[current_date] = {
                        "date": str(current_date),
                        "temp_c": item["main"]["temp"],
                        "condition": item["weather"][0]["description"],
                    }

        forecasts = [daily_forecasts[d] for d in sorted(daily_forecasts.keys())]

        # Step 2: Fallback to current weather if trip is beyond 5-day forecast
        if not forecasts:
            logger.info(
                "Trip is beyond 5-day forecast range. Fetching current weather as context."
            )
            current_url = "https://api.openweathermap.org/data/2.5/weather"
            current_data = await fetch_json(current_url, params=params)

            return {
                "forecasts": [],
                "current_context": {
                    "temp_c": current_data["main"]["temp"],
                    "condition": current_data["weather"][0]["description"],
                },
                "source": "OpenWeatherMap",
                "message": "Trip is beyond the 5-day forecast range. Showing current weather for context.",
                "retrieved_at": datetime.utcnow().isoformat(),
            }

        return {
            "forecasts": forecasts,
            "current_context": None,
            "source": "OpenWeatherMap",
            "message": "Forecast retrieved successfully.",
            "retrieved_at": datetime.utcnow().isoformat(),
        }

    except Exception as e:
        logger.error(f"Weather API failed: {str(e)}")
        return {
            "forecasts": [],
            "current_context": None,
            "source": "Error Fallback",
            "message": f"Weather data unavailable: {str(e)}",
            "retrieved_at": datetime.utcnow().isoformat(),
        }
