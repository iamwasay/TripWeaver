from app.models.schemas import TripRequest, AgentResult
from app.tools.flights import get_flights
from app.utils.logger import logger


async def run_flight_agent(request: TripRequest) -> AgentResult:
    logger.info("Flight Agent running...")
    try:
        flights = await get_flights(
            origin=request.origin,
            destination=request.destination,
            depart_date=request.start_date.isoformat(),
            return_date=request.end_date.isoformat(),  # Added return date for round trips
            adults=request.travelers,
        )
        return AgentResult(
            agent_name="FlightAgent",
            status="success",
            data=flights,
            source=flights[0]["source"] if flights else "None",
            warnings=["Prices are estimates and subject to change."],
        )
    except Exception as e:
        logger.error(f"Flight Agent failed: {e}")
        return AgentResult(agent_name="FlightAgent", status="error", errors=[str(e)])
