from app.models.schemas import TripRequest, AgentResult
from app.tools.hotels import get_hotels
from app.utils.logger import logger


async def run_stay_agent(request: TripRequest) -> AgentResult:
    logger.info("Stay Agent running...")
    try:
        hotels = await get_hotels(
            destination=request.destination,
            checkin=request.start_date.isoformat(),
            checkout=request.end_date.isoformat(),
        )
        return AgentResult(
            agent_name="StayAgent",
            status="success",
            data=hotels,
            source=hotels[0]["source"] if hotels else "None",
        )
    except Exception as e:
        logger.error(f"Stay Agent failed: {e}")
        return AgentResult(agent_name="StayAgent", status="error", errors=[str(e)])
