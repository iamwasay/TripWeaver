from datetime import datetime
from app.config import get_settings
from app.services.api_client import fetch_json
from app.utils.logger import logger
from app.utils.locations import get_city_name

settings = get_settings()

# A small database of real, verified ticket prices for famous landmarks
VERIFIED_PRICES = {
    "louvre": (22.0, "EUR"),
    "colosseum": (18.0, "EUR"),
    "hagia sophia": (25.0, "EUR"),
    "eiffel tower": (29.0, "EUR"),
    "burj khalifa": (40.0, "USD"),
    "buckingham palace": (30.0, "GBP"),
    "tokyo skytree": (21.0, "USD"),
    "petronas twin towers": (20.0, "USD"),
}


async def search_activities(destination: str, interests: list[str]) -> list[dict]:
    if not settings.geoapify_api_key:
        logger.warning("No GEOAPIFY_API_KEY found. Using mock activities.")
        return [
            {
                "name": f"City Museum of {destination}",
                "category": "cultural",
                "estimated_duration_hours": 2.0,
                "cost": 15.0,
                "currency": "USD",
                "source": "Mock Data",
                "retrieved_at": datetime.utcnow().isoformat(),
                "is_estimated": True,
                "price_source": "Mock Estimate",
            }
        ]

    city_query = get_city_name(destination)
    logger.info(f"Searching real activities via Geoapify for {city_query}")

    try:
        geo_url = f"https://api.geoapify.com/v1/geocode/search?text={city_query}&limit=1&apiKey={settings.geoapify_api_key}"
        geo_data = await fetch_json(geo_url)

        if not geo_data.get("features"):
            raise ValueError("Could not find coordinates for destination.")

        lon = geo_data["features"][0]["properties"]["lon"]
        lat = geo_data["features"][0]["properties"]["lat"]

        places_url = f"https://api.geoapify.com/v2/places?categories=tourism.sights,tourism.attraction&filter=circle:{lon},{lat},10000&limit=5&apiKey={settings.geoapify_api_key}"
        places_data = await fetch_json(places_url)

        activities = []
        seen_names = set()

        for place in places_data.get("features", []):
            props = place["properties"]
            name = props.get("name", "Unknown Attraction")

            if not name or name.lower() == "unknown attraction" or name in seen_names:
                continue
            seen_names.add(name)

            lower_name = name.lower()

            # 1. Check for Verified Prices
            verified_found = False
            for landmark, (price, currency) in VERIFIED_PRICES.items():
                if landmark in lower_name:
                    activities.append(
                        {
                            "name": name,
                            "category": "attraction",
                            "estimated_duration_hours": 2.0,
                            "cost": price,
                            "currency": currency,
                            "address": props.get("formatted", ""),
                            "source": "Geoapify",
                            "retrieved_at": datetime.utcnow().isoformat(),
                            "is_estimated": False,
                            "price_source": "Verified Landmark Ticket",
                        }
                    )
                    verified_found = True
                    break

            if verified_found:
                continue

            # 2. Fallback to Estimate
            cost = 10.0
            if any(w in lower_name for w in ["museum", "palace", "tower", "park"]):
                cost = 25.0
            elif any(w in lower_name for w in ["mosque", "street", "walk", "beach"]):
                cost = 0.0

            activities.append(
                {
                    "name": name,
                    "category": "attraction",
                    "estimated_duration_hours": 2.0,
                    "cost": cost,
                    "currency": "USD",
                    "address": props.get("formatted", ""),
                    "source": "Geoapify",
                    "retrieved_at": datetime.utcnow().isoformat(),
                    "is_estimated": True,
                    "price_source": "Algorithm Estimate",
                }
            )

        return activities

    except Exception as e:
        logger.error(f"Geoapify API failed: {str(e)}")
        return [
            {
                "name": f"{destination} City Tour",
                "category": "sightseeing",
                "estimated_duration_hours": 2.0,
                "cost": 10.0,
                "currency": "USD",
                "source": "Mock Fallback",
                "retrieved_at": datetime.utcnow().isoformat(),
                "is_estimated": True,
                "price_source": "Fallback Estimate",
            }
        ]
