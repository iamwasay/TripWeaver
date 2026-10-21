from datetime import datetime
from app.config import get_settings
from app.services.api_client import fetch_json
from app.utils.logger import logger
from app.utils.locations import get_city_name

settings = get_settings()


async def get_hotels(destination: str, checkin: str, checkout: str) -> list[dict]:
    if not settings.serpapi_api_key:
        logger.warning("No SERPAPI_API_KEY found. Using mock hotel data.")
        return _get_mock_hotels(destination, checkin, checkout)

    # Translate IATA code to City Name
    city_query = get_city_name(destination)
    logger.info(f"Fetching real hotels via SerpApi for {city_query}")

    try:
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_hotels",
            "q": city_query,
            "check_in_date": checkin,
            "check_out_date": checkout,
            "currency": "USD",
            "api_key": settings.serpapi_api_key,
        }

        data = await fetch_json(url, params=params)

        hotels = []
        for prop in data.get("properties", [])[:3]:  # Get top 3
            rate = prop.get("rate_per_night", {}).get("extracted_lowest", 100.0)

            hotels.append(
                {
                    "property_name": prop.get("name", "Hotel"),
                    "room_type": "Standard Room",
                    "nightly_rate": float(rate),
                    "total_stay_cost": float(rate)
                    * max(
                        1,
                        (
                            datetime.fromisoformat(checkout)
                            - datetime.fromisoformat(checkin)
                        ).days,
                    ),
                    "currency": "USD",
                    "rating": prop.get("overall_rating", 4.0),
                    "source": "Google Hotels (SerpApi)",
                    "retrieved_at": datetime.utcnow().isoformat(),
                }
            )

        if not hotels:
            logger.warning("No real hotels found. Using mock.")
            return _get_mock_hotels(destination, checkin, checkout)

        return hotels
    except Exception as e:
        logger.error(f"SerpApi Hotels failed: {str(e)}. Falling back to mock.")
        return _get_mock_hotels(destination, checkin, checkout)


def _get_mock_hotels(destination: str, checkin: str, checkout: str) -> list[dict]:
    nights = (datetime.fromisoformat(checkout) - datetime.fromisoformat(checkin)).days
    return [
        {
            "property_name": "The Ritz-Carlton (Mock)",
            "room_type": "Deluxe Room",
            "nightly_rate": 250.0,
            "total_stay_cost": 250.0 * max(1, nights),
            "currency": "USD",
            "rating": 4.8,
            "source": "Mock Data",
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    ]
