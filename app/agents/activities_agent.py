from app.models.schemas import TripRequest, AgentResult
from app.tools.places import search_activities
from app.utils.logger import logger


async def run_activities_agent(request: TripRequest) -> AgentResult:
    logger.info("Activities Agent running...")
    try:
        activities = await search_activities(
            destination=request.destination, interests=request.interests
        )
        return AgentResult(
            agent_name="ActivitiesAgent",
            status="success",
            data=activities,
            source=activities[0]["source"] if activities else "None",
        )
    except Exception as e:
        logger.error(f"Activities Agent failed: {e}")
        return AgentResult(
            agent_name="ActivitiesAgent", status="error", errors=[str(e)]
        )
