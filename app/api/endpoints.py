from fastapi import APIRouter, HTTPException
from app.models.schemas import TripRequest, TripState
from app.agents.orchestrator import orchestrate_trip
from app.services.database import save_trip, count_trips, DATABASE_URL
from app.utils.locations import get_popular_airports
from app.utils.logger import logger

router = APIRouter()


@router.post(
    "/plan-trip",
    response_model=TripState,
    summary="Generate a complete multi-agent travel plan",
)
async def create_trip_plan(request: TripRequest):
    """
    Accepts a TripRequest, runs the full multi-agent workflow,
    saves it to the database, and returns the complete TripState.
    """
    try:
        logger.info(
            f"New API request received: {request.origin} -> {request.destination}"
        )

        state = await orchestrate_trip(request)

        # Safely attempt to save to DB. If this fails, we DO NOT crash the response.
        try:
            save_trip(
                trip_id=state.trip_id,
                destination=request.destination,
                budget=request.budget_amount,
                status=state.validation.get("status")
                if state.validation
                else "UNKNOWN",
                payload=state.model_dump(mode="json"),
            )
        except Exception as db_err:
            logger.warning(f"Audit log failed (trip still returned): {db_err}")

        return state

    except Exception as e:
        logger.error(f"API Error during trip planning: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/airports", summary="Get list of major global airports for UI dropdown")
def get_airports():
    try:
        return get_popular_airports()
    except Exception as e:
        logger.error(f"Failed to load airports: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not load airport database.")


@router.get("/db-status", summary="Check database status and persistence")
def db_status():
    """
    Returns the current database provider and record count.
    Useful for confirming whether the DB is persistent.
    """
    provider = DATABASE_URL.split("://")[0]
    count = count_trips()
    return {
        "provider": provider,
        "is_persistent": provider
        != "sqlite",  # SQLite on Render free tier is ephemeral
        "record_count": count if count >= 0 else "Unavailable",
        "note": (
            "SQLite on Render's free tier is ephemeral and resets on restart. "
            "For persistence, configure DATABASE_URL to point to a PostgreSQL instance."
            if provider == "sqlite"
            else "Connected to a persistent database."
        ),
    }
