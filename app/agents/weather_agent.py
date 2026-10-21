from app.models.schemas import TripRequest, AgentResult
from app.tools.weather import get_weather_context
from app.utils.logger import logger


async def run_weather_agent(request: TripRequest) -> AgentResult:
    logger.info("Weather Agent running...")
    try:
        weather = await get_weather_context(request.destination)
        return AgentResult(
            agent_name="WeatherAgent",
            status="success",
            data=weather,
            source=weather["source"],
        )
    except Exception as e:
        logger.error(f"Weather Agent failed: {e}")
        return AgentResult(agent_name="WeatherAgent", status="error", errors=[str(e)])
