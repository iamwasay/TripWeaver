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

    city_query = get_city_name(destination)
    logger.info(f"Fetching real hotels via SerpApi for {city_query}")

    try:
        # Calculate nights to use as fallback
        from datetime import date

        nights = max(
            1,
            (
                datetime.fromisoformat(checkout).date()
                - datetime.fromisoformat(checkin).date()
            ).days,
        )

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
        for prop in data.get("properties", [])[:5]:  # Look at top 5
            try:
                rate_info = prop.get("rate_per_night", {})
                nightly = float(rate_info.get("extracted_lowest", 0.0))

                # Check for total_rate (usually includes taxes)
                total_info = prop.get("total_rate", {})
                total_cost = total_info.get("extracted_lowest")

                if total_cost is not None:
                    total_cost = float(total_cost)
                else:
                    total_cost = nightly * nights

                taxes_info = prop.get("taxes_and_fees", {})
                taxes = (
                    float(taxes_info.get("extracted_lowest", 0.0))
                    if taxes_info
                    else 0.0
                )

                # FIX: Skip hotels with missing or zero prices
                if nightly <= 0 and total_cost <= 0:
                    continue

                # If total_cost is 0 but nightly is > 0, recalculate
                if total_cost <= 0 and nightly > 0:
                    total_cost = nightly * nights

                hotels.append(
                    {
                        "property_name": prop.get("name", "Hotel"),
                        "room_type": "Standard Room",
                        "nightly_rate": nightly,
                        "total_stay_cost": total_cost,
                        "taxes_and_fees": taxes,
                        "currency": "USD",
                        "rating": prop.get("overall_rating", 4.0),
                        "source": "Google Hotels (SerpApi)",
                        "retrieved_at": datetime.utcnow().isoformat(),
                    }
                )
            except Exception as e:
                logger.warning(f"Skipping malformed hotel data: {e}")
                continue

        if not hotels:
            logger.warning("No valid real hotels found. Using mock.")
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
            "taxes_and_fees": 0.0,
            "currency": "USD",
            "rating": 4.8,
            "source": "Mock Data",
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    ]
