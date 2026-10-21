"""TripWeaver — Multi-Agent Budget Travel Planner.

FastAPI entry point.
"""

from fastapi import FastAPI

from app.config import get_settings
from app.api.endpoints import router as api_router

settings = get_settings()

app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description=(
        "Multi-agent budget travel planner. "
        "MVP — search & recommendation only, no automatic booking."
    ),
)

# Include the multi-agent workflow API routes
app.include_router(api_router, prefix="/api/v1")


@app.get("/")
def root() -> dict:
    """Human-friendly landing response."""
    return {
        "app": settings.app_name,
        "version": settings.app_version,
        "status": "ok",
        "docs": "/docs",
        "health": "/health",
    }


@app.get("/health")
def health() -> dict:
    """Liveness probe. Used by Docker, uptime checks, and tests."""
    return {
        "status": "healthy",
        "environment": settings.app_env,
    }
