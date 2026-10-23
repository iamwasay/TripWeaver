from app.models.schemas import TripRequest, AgentResult
from app.tools.weather import get_weather_forecast
from app.utils.logger import logger


async def run_weather_agent(request: TripRequest) -> AgentResult:
    logger.info("Weather Agent running...")
    try:
        weather_data = await get_weather_forecast(
            destination=request.destination,
            start_date_str=request.start_date.isoformat(),
            end_date_str=request.end_date.isoformat(),
        )
        return AgentResult(
            agent_name="WeatherAgent",
            status="success",
            data=weather_data,
            source=weather_data.get("source", "Unknown"),
        )
    except Exception as e:
        logger.error(f"Weather Agent failed: {e}")
        return AgentResult(agent_name="WeatherAgent", status="error", errors=[str(e)])
