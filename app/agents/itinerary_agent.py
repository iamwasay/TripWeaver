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
        # Calculate total days (inclusive of start and end)
        days_count = (request.end_date - request.start_date).days + 1
        if days_count < 1:
            days_count = 1

        raw_activities = activities_result.data or []
        activities = [ActivityOption(**a) for a in raw_activities]

        # Pace → max activities per day
        pace = (request.pace or "moderate").lower()
        if pace == "relaxed":
            max_per_day = 1
        elif pace == "packed":
            max_per_day = 4
        else:
            max_per_day = 2

        # Parse flight times
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
        scheduling_warnings = []

        # --- Edge Case: One-Day Trip ---
        if days_count == 1:
            day_notes = ["One-day trip. Check-in and check-out on the same day."]

            if arrival_time and departure_time:
                # Calculate time at destination
                time_available_hours = (
                    departure_time - arrival_time
                ).total_seconds() / 3600
                day_notes.append(
                    f"Time at destination: ~{time_available_hours:.1f} hours."
                )

                if time_available_hours < 4:
                    day_notes.append("Very short stay - no activities scheduled.")
                    scheduling_warnings.append(
                        f"One-day trip with only {time_available_hours:.1f}h at destination. "
                        "No activities scheduled."
                    )
                    days.append(
                        DailySchedule(
                            day_number=1,
                            date=request.start_date,
                            activities=[],
                            notes=day_notes,
                        )
                    )
                else:
                    # Schedule up to max_per_day activities
                    day_activities = activities[:max_per_day]
                    activity_idx = len(day_activities)
                    days.append(
                        DailySchedule(
                            day_number=1,
                            date=request.start_date,
                            activities=day_activities,
                            notes=day_notes,
                        )
                    )
            else:
                days.append(
                    DailySchedule(
                        day_number=1,
                        date=request.start_date,
                        activities=[],
                        notes=day_notes,
                    )
                )

            itinerary = Itinerary(days=days)
            status = (
                "warning"
                if (
                    scheduling_warnings
                    or (
                        validation_result.data
                        and validation_result.data.get("status") == "FAIL"
                    )
                )
                else "success"
            )
            return AgentResult(
                agent_name="ItineraryAgent",
                status=status,
                data=itinerary.model_dump(mode="json"),
                warnings=scheduling_warnings,
            )

        # --- Multi-Day Trip ---
        for i in range(days_count):
            current_date = request.start_date + timedelta(days=i)
            day_notes = []
            day_activities = []

            # --- Day 1: Arrival Day ---
            if i == 0:
                if arrival_time:
                    day_notes.append(f"Arrival at {arrival_time.strftime('%H:%M')}.")

                    # Late night arrivals → no activities
                    if arrival_time.hour >= 18:
                        day_notes.append(
                            "Late evening/night arrival - no activities scheduled today."
                        )
                        scheduling_warnings.append(
                            f"Late arrival ({arrival_time.strftime('%H:%M')}) - Day 1 has no activities."
                        )
                        days.append(
                            DailySchedule(
                                day_number=1,
                                date=current_date,
                                activities=[],
                                notes=day_notes,
                            )
                        )
                        continue

                    # Afternoon arrivals → limited activities
                    elif arrival_time.hour >= 14:
                        day_notes.append(
                            "Afternoon arrival - limited activities to allow for check-in."
                        )
                        max_per_day_today = 1
                    else:
                        day_notes.append("Morning arrival - full day available.")
                        max_per_day_today = max_per_day
                else:
                    day_notes.append("Arrival day (flight time unknown).")
                    max_per_day_today = max_per_day

            # --- Last Day: Departure Day ---
            elif i == days_count - 1:
                if departure_time:
                    # Calculate when user must leave for airport (3 hours before)
                    must_leave = departure_time - timedelta(hours=3)
                    day_notes.append(
                        f"Departure at {departure_time.strftime('%H:%M')}. "
                        f"Must leave for airport by {must_leave.strftime('%H:%M')}."
                    )

                    # Early morning departures → no activities
                    if departure_time.hour < 10:
                        day_notes.append(
                            "Early morning departure - no activities scheduled today."
                        )
                        scheduling_warnings.append(
                            f"Early departure ({departure_time.strftime('%H:%M')}) - last day has no activities."
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

                    # Morning departures → limited activities
                    elif must_leave.hour < 12:
                        day_notes.append("Morning departure - limited activities only.")
                        max_per_day_today = 1
                    else:
                        max_per_day_today = max_per_day
                else:
                    day_notes.append("Departure day (flight time unknown).")
                    max_per_day_today = max_per_day

            # --- Regular Day ---
            else:
                max_per_day_today = max_per_day

            # Distribute activities
            while (
                activity_idx < len(activities)
                and len(day_activities) < max_per_day_today
            ):
                day_activities.append(activities[activity_idx])
                activity_idx += 1

            if len(day_activities) > 1:
                day_notes.append("1-hour travel buffer added between each activity.")
            elif not day_activities and 0 < i < days_count - 1:
                day_notes.append("Free day - explore at your own pace.")

            days.append(
                DailySchedule(
                    day_number=i + 1,
                    date=current_date,
                    activities=day_activities,
                    notes=day_notes,
                )
            )

        # Warn about unscheduled activities
        if activity_idx < len(activities):
            leftover = len(activities) - activity_idx
            days[-1].notes.append(
                f"{leftover} additional activities found but could not fit in the schedule."
            )
            scheduling_warnings.append(
                f"{leftover} activities could not be scheduled due to time constraints."
            )

        itinerary = Itinerary(days=days)

        # Determine status
        status = "success"
        if scheduling_warnings:
            status = "warning"
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
            warnings=scheduling_warnings,
        )

    except Exception as e:
        logger.error(f"Itinerary Agent failed: {e}")
        return AgentResult(agent_name="ItineraryAgent", status="error", errors=[str(e)])
