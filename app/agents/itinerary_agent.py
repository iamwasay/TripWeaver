from app.models.schemas import (
    TripRequest,
    AgentResult,
    Itinerary,
    DailySchedule,
    ActivityOption,
)
from app.utils.logger import logger
from datetime import timedelta


async def run_itinerary_agent(
    request: TripRequest, activities_result: AgentResult
) -> AgentResult:
    logger.info("Itinerary Agent running...")

    try:
        days_count = (request.end_date - request.start_date).days
        raw_activities = activities_result.data or []

        # Convert dicts back to ActivityOption models
        activities = [ActivityOption(**a) for a in raw_activities]

        days = []
        # Distribute activities evenly across the days (simple MVP logic)
        activities_per_day = (
            max(1, len(activities) // days_count) if days_count > 0 else 1
        )

        for i in range(days_count):
            current_date = request.start_date + timedelta(days=i)
            start_idx = i * activities_per_day
            end_idx = start_idx + activities_per_day

            day_activities = activities[start_idx:end_idx]

            days.append(
                DailySchedule(
                    day_number=i + 1,
                    date=current_date,
                    activities=day_activities,
                    notes=["Arrival & Check-in" if i == 0 else "Explore destination"],
                )
            )

        itinerary = Itinerary(days=days)

        return AgentResult(
            agent_name="ItineraryAgent",
            status="success",
            data=itinerary.model_dump(mode="json"),
        )
    except Exception as e:
        logger.error(f"Itinerary Agent failed: {e}")
        return AgentResult(agent_name="ItineraryAgent", status="error", errors=[str(e)])
