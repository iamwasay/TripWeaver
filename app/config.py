"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict
from app.utils.logger import logger


class Settings(BaseSettings):
    """Settings are read from .env (local) or environment variables (prod)."""

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=False,
        extra="ignore",
    )

    # --- App ---
    app_env: str = "development"
    app_name: str = "TripWeaver"
    app_version: str = "0.1.0"

    # --- LLM (Optional / Future) ---
    openai_api_key: str = ""
    groq_api_key: str = ""

    # --- Flights & Hotels ---
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    serpapi_api_key: str = ""

    # --- Places / Maps ---
    google_maps_api_key: str = ""
    opentripmap_api_key: str = ""
    geoapify_api_key: str = ""

    # --- Weather & Currency ---
    weather_api_key: str = ""
    fx_api_key: str = ""

    # --- Database ---
    database_url: str = "sqlite:///./tripweaver.db"

    # --- Optional Cache/Queue ---
    redis_url: str = ""

    @property
    def is_development(self) -> bool:
        return self.app_env.lower() == "development"


@lru_cache
def get_settings() -> Settings:
    """Cached so the .env is only parsed once per process."""
    settings = Settings()

    # --- Validation & Diagnostics ---
    required_keys = {
        "SERPAPI_API_KEY": settings.serpapi_api_key,
        "GEOAPIFY_API_KEY": settings.geoapify_api_key,
        "WEATHER_API_KEY": settings.weather_api_key,
    }

    missing = [k for k, v in required_keys.items() if not v]

    if missing:
        logger.warning(
            f"⚠️ Missing API keys: {', '.join(missing)}. "
            f"The app will run, but related agents will fall back to Mock Data."
        )
    else:
        logger.info("✅ All required API keys are loaded.")

    return settings
