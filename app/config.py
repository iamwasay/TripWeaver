"""Application configuration loaded from environment variables."""

from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict


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
    # Amadeus is kept for legacy/future use, but SerpApi is our active provider
    amadeus_client_id: str = ""
    amadeus_client_secret: str = ""
    serpapi_api_key: str = ""

    # --- Places / Maps ---
    # Geoapify is our active provider. OpenTripMap and Google are fallbacks/legacy.
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
    return Settings()
