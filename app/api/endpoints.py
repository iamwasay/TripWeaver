from fastapi import APIRouter, HTTPException
from app.models.schemas import TripRequest, TripState
from app.agents.orchestrator import orchestrate_trip
from app.services.database import save_trip
from app.utils.locations import get_popular_airports
from app.utils.logger import logger

# Create a router for our API
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

        # 1. Run the LangGraph orchestrator
        state = await orchestrate_trip(request)

        # 2. Save the result to the SQLite database for audit trails
        save_trip(
            trip_id=state.trip_id,
            destination=request.destination,
            budget=request.budget_amount,
            status=state.validation["status"] if state.validation else "UNKNOWN",
            payload=state.model_dump(mode="json"),
        )

        # 3. Return the final state to the frontend
        return state

    except Exception as e:
        logger.error(f"API Error during trip planning: {str(e)}")
        raise HTTPException(status_code=500, detail=str(e))


@router.get("/airports", summary="Get list of major global airports for UI dropdown")
def get_airports():
    """
    Returns a massive list of formatted airports (City (CODE)).
    It merges the manual dictionary and the CSV file.
    """
    try:
        airports = get_popular_airports()
        return airports
    except Exception as e:
        logger.error(f"Failed to load airports: {str(e)}")
        raise HTTPException(status_code=500, detail="Could not load airport database.")
