from app.models.schemas import TripRequest, AgentResult
from app.tools.flights import get_flights
from app.utils.logger import logger
from datetime import datetime


async def run_flight_agent(request: TripRequest) -> AgentResult:
    logger.info("Flight Agent running...")
    try:
        flights = await get_flights(
            origin=request.origin,
            destination=request.destination,
            date=request.start_date.isoformat(),
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
        },
        {
            "airline": "Turkish Airlines (Mock)",
            "departure_time": f"{date}T06:00:00",
            "arrival_time": f"{date}T12:00:00",
            "price": 600.0 * adults,
            "currency": "USD",
            "source": "Mock Data",
            "retrieved_at": datetime.utcnow().isoformat(),
        },
    ]
