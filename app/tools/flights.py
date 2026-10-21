from datetime import datetime
from app.config import get_settings
from app.services.api_client import fetch_json
from app.utils.logger import logger

settings = get_settings()


async def get_flights(
    origin: str, destination: str, date: str, adults: int
) -> list[dict]:
    if not settings.serpapi_api_key:
        logger.warning("No SERPAPI_API_KEY found. Using mock flight data.")
        return _get_mock_flights(origin, destination, adults, date)

    logger.info(f"Fetching real flights via SerpApi: {origin} -> {destination}")
    try:
        # Note: SerpApi Google Flights works best with IATA codes (e.g., ISB, IST).
        # If the user types a city name, it might fail and fall back to mock.
        url = "https://serpapi.com/search.json"
        params = {
            "engine": "google_flights",
            "departure_id": origin,
            "arrival_id": destination,
            "outbound_date": date,
            "type": "2",  # One-way
            "currency": "USD",
            "adults": adults,
            "api_key": settings.serpapi_api_key,
        }

        data = await fetch_json(url, params=params)

        flights = []
        # SerpApi returns "best_flights" and "other_flights"
        for flight_group in data.get("best_flights", [])[:3]:  # Get top 3
            first_leg = flight_group["flights"][0]
            last_leg = flight_group["flights"][-1]

            flights.append(
                {
                    "airline": first_leg["airline"],
                    "departure_time": first_leg["departure_airport"]["time"],
                    "arrival_time": last_leg["arrival_airport"]["time"],
                    "price": float(flight_group["price"]),
                    "currency": "USD",
                    "source": "Google Flights (SerpApi)",
                    "retrieved_at": datetime.utcnow().isoformat(),
                }
            )

        if not flights:
            logger.warning("No real flights found for these dates. Using mock.")
            return _get_mock_flights(origin, destination, adults, date)

        return flights
    except Exception as e:
        logger.error(f"SerpApi failed: {str(e)}. Falling back to mock.")
        return _get_mock_flights(origin, destination, adults, date)


def _get_mock_flights(
    origin: str, destination: str, adults: int, date: str
) -> list[dict]:
    return [
        {
            "airline": "Emirates (Mock)",
            "departure_time": f"{date}T03:00:00",
            "arrival_time": f"{date}T11:00:00",
            "price": 450.0 * adults,
            "currency": "USD",
            "source": "Mock Data",
            "retrieved_at": datetime.utcnow().isoformat(),
        }
    ]
