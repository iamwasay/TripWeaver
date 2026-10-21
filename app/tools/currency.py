from datetime import datetime
from app.services.api_client import fetch_json
from app.utils.logger import logger

# A simple in-memory cache so we don't call the API multiple times per run
_cache = {}


async def get_exchange_rate(from_currency: str, to_currency: str) -> dict:
    """
    Fetches the exchange rate between two currencies.
    Returns a dictionary with the rate and the source timestamp.
    """
    from_currency = from_currency.upper()
    to_currency = to_currency.upper()

    if from_currency == to_currency:
        return {"rate": 1.0, "source": "internal", "retrieved_at": datetime.utcnow()}

    # Check cache first
    cache_key = f"{from_currency}_{to_currency}"
    if cache_key in _cache:
        logger.info(f"Using cached exchange rate for {cache_key}")
        return _cache[cache_key]

    # open.er-api.com is free and requires no API key
    url = f"https://open.er-api.com/v6/latest/{from_currency}"
    logger.info(f"Fetching live exchange rate: {from_currency} -> {to_currency}")

    try:
        data = await fetch_json(url)

        if "rates" not in data or to_currency not in data["rates"]:
            raise ValueError(f"Currency {to_currency} not supported by the API.")

        rate = data["rates"][to_currency]

        result = {
            "rate": rate,
            "source": "open.er-api.com",
            "retrieved_at": datetime.utcnow(),
        }

        # Save to cache
        _cache[cache_key] = result
        return result

    except Exception as e:
        logger.error(f"Failed to fetch exchange rate: {str(e)}")
        # Fallback to 1.0 so the app doesn't crash (though budget will be inaccurate)
        return {
            "rate": 1.0,
            "source": "fallback_error",
            "retrieved_at": datetime.utcnow(),
            "error": str(e),
        }
