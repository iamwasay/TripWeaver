from datetime import datetime
from app.config import get_settings
from app.services.api_client import fetch_json
from app.utils.logger import logger
from app.utils.locations import get_city_name

settings = get_settings()


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
            }
        ]

    # Translate IATA code to City Name
    city_query = get_city_name(destination)
    logger.info(f"Searching real activities via Geoapify for {city_query}")

    try:
        # Step 1: Geocode the destination to get lat/lon
        geo_url = f"https://api.geoapify.com/v1/geocode/search?text={city_query}&limit=1&apiKey={settings.geoapify_api_key}"
        geo_data = await fetch_json(geo_url)

        if not geo_data.get("features"):
            raise ValueError("Could not find coordinates for destination.")

        lon = geo_data["features"][0]["properties"]["lon"]
        lat = geo_data["features"][0]["properties"]["lat"]

        # Step 2: Find tourist attractions near those coordinates (10km radius)
        places_url = f"https://api.geoapify.com/v2/places?categories=tourism.sights,tourism.attraction&filter=circle:{lon},{lat},10000&limit=5&apiKey={settings.geoapify_api_key}"
        places_data = await fetch_json(places_url)

        activities = []
        seen_names = set()

        for place in places_data.get("features", []):
            props = place["properties"]
            name = props.get("name", "Unknown Attraction")

            # FIX: Skip if name is empty, "Unknown Attraction", or a duplicate
            if not name or name.lower() == "unknown attraction" or name in seen_names:
                continue
            seen_names.add(name)

            # Dynamic Cost Estimation
            cost = 10.0
            lower_name = name.lower()
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
            }
        ]
