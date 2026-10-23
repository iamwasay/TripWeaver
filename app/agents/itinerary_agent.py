from app.models.schemas import (
    TripRequest,
    AgentResult,
    Itinerary,
    DailySchedule,
    ActivityOption,
)
from app.utils.logger import logger
from datetime import timedelta, datetime


async def run_itinerary_agent(
    request: TripRequest,
    activities_result: AgentResult,
    flight_result: AgentResult,
    validation_result: AgentResult,
) -> AgentResult:
    logger.info("Itinerary Agent running...")

    try:
        days_count = (request.end_date - request.start_date).days + 1
        if days_count < 1:
            days_count = 1

        raw_activities = activities_result.data or []
        activities = [ActivityOption(**a) for a in raw_activities]

        pace = (request.pace or "moderate").lower()
        if pace == "relaxed":
            max_per_day = 1
        elif pace == "packed":
            max_per_day = 4
        else:
            max_per_day = 2

        arrival_time = None
        departure_time = None
        if flight_result and flight_result.data:
            f = flight_result.data[0]
            try:
                arr_str = str(f.get("arrival_time", ""))
                dep_str = str(f.get("departure_time", ""))
                if arr_str:
                    arrival_time = datetime.fromisoformat(
                        arr_str.replace("Z", "+00:00")
                    )
                if dep_str:
                    departure_time = datetime.fromisoformat(
                        dep_str.replace("Z", "+00:00")
                    )
            except Exception as e:
                logger.warning(f"Could not parse flight times: {e}")

        days = []
        activity_idx = 0

        for i in range(days_count):
            current_date = request.start_date + timedelta(days=i)
            day_notes = []
            day_activities = []

            if i == 0:
                if arrival_time:
                    ready_time = arrival_time + timedelta(hours=2)
                    day_notes.append(
                        f"Arrival at {arrival_time.strftime('%H:%M')}. Buffer for check-in and rest."
                    )
                    if ready_time.hour >= 16:
                        day_notes.append(
                            "No activities scheduled to allow for rest after travel."
                        )
                        days.append(
                            DailySchedule(
                                day_number=i + 1,
                                date=current_date,
                                activities=[],
                                notes=day_notes,
                            )
                        )
                        continue
                else:
                    day_notes.append("Arrival & Check-in.")

            elif i == days_count - 1:
                if departure_time:
                    must_leave_time = departure_time - timedelta(hours=3)
                    day_notes.append(
                        f"Departure at {departure_time.strftime('%H:%M')}. Must leave for airport by {must_leave_time.strftime('%H:%M')}."
                    )
                    if must_leave_time.hour < 12:
                        day_notes.append("No activities scheduled due to early flight.")
                        days.append(
                            DailySchedule(
                                day_number=i + 1,
                                date=current_date,
                                activities=[],
                                notes=day_notes,
                            )
                        )
                        continue
                else:
                    day_notes.append("Departure & Check-out.")

            while activity_idx < len(activities) and len(day_activities) < max_per_day:
                day_activities.append(activities[activity_idx])
                activity_idx += 1

            if day_activities:
                day_notes.append("Travel buffer of 1 hour added between activities.")
            elif i > 0 and i < days_count - 1:
                day_notes.append("Free time / Explore the city at your own pace.")

            days.append(
                DailySchedule(
                    day_number=i + 1,
                    date=current_date,
                    activities=day_activities,
                    notes=day_notes,
                )
            )

        if activity_idx < len(activities):
            leftover = len(activities) - activity_idx
            days[-1].notes.append(
                f"Note: {leftover} additional activities were found but could not fit within the schedule."
            )

        itinerary = Itinerary(days=days)

        status = "success"
        if (
            validation_result
            and validation_result.data
            and validation_result.data.get("status") == "FAIL"
        ):
            status = "warning"

        return AgentResult(
            agent_name="ItineraryAgent",
            status=status,
            data=itinerary.model_dump(mode="json"),
        )
    except Exception as e:
        logger.error(f"Itinerary Agent failed: {e}")
        return AgentResult(agent_name="ItineraryAgent", status="error", errors=[str(e)])
