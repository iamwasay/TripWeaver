from datetime import datetime
from app.models.schemas import TripRequest, AgentResult, ValidationResult
from app.utils.logger import logger


async def run_verification_agent(
    request: TripRequest,
    budget_result: AgentResult,
    flight_result: AgentResult,
    stay_result: AgentResult,
    itinerary_result: AgentResult = None,
) -> AgentResult:
    logger.info("Verification Agent running...")

    issues = []

    try:
        # --- 1. Budget Check ---
        budget = budget_result.data
        if not budget:
            issues.append("Budget calculation failed.")
        elif budget.get("over_budget_amount", 0) > 0:
            issues.append(
                f"Over budget by {budget['over_budget_amount']:,.2f} {request.budget_currency}."
            )

        # --- 2. Missing Flights/Hotels Check ---
        if not flight_result.data or flight_result.status == "error":
            issues.append("No valid flights were found for this route.")
        if not stay_result.data or stay_result.status == "error":
            issues.append("No valid hotels were found for these dates.")

        # --- 3. Travel Dates Validation ---
        if request.end_date <= request.start_date:
            issues.append(
                "Invalid trip dates: return date must be after departure date."
            )

        trip_days = (request.end_date - request.start_date).days
        if trip_days < 1:
            issues.append("Trip must be at least 1 night.")

        # --- 4. Flight Timing Validation ---
        if flight_result.data:
            f = flight_result.data[0]
            try:
                dep_str = str(f.get("departure_time", ""))
                arr_str = str(f.get("arrival_time", ""))
                if dep_str and arr_str:
                    dep = datetime.fromisoformat(dep_str.replace("Z", "+00:00"))
                    arr = datetime.fromisoformat(arr_str.replace("Z", "+00:00"))
                    if arr <= dep:
                        issues.append(
                            "Flight data invalid: arrival time is before departure time."
                        )
                    # Check flight duration sanity (must be > 30 mins and < 48 hours)
                    duration_hours = (arr - dep).total_seconds() / 3600
                    if duration_hours < 0.5:
                        issues.append(
                            "Flight data suspicious: flight duration under 30 minutes."
                        )
                    elif duration_hours > 48:
                        issues.append(
                            "Flight data suspicious: flight duration over 48 hours."
                        )
            except (ValueError, TypeError):
                pass  # Skip if dates can't be parsed

        # --- 5. Hotel Date Alignment ---
        # Note: Our StayAgent is designed to use the trip dates directly,
        # so we're validating that the request has sane dates for the hotel.
        if flight_result.data and stay_result.data:
            # Check that the stay was long enough
            nights = (request.end_date - request.start_date).days
            stay_cost = stay_result.data[0].get("total_stay_cost", 0)
            nightly = stay_result.data[0].get("nightly_rate", 0)
            if nightly > 0 and stay_cost > 0:
                calculated_nights = stay_cost / nightly
                if abs(calculated_nights - nights) > 1:
                    issues.append(
                        f"Hotel data mismatch: {calculated_nights:.0f} nights calculated "
                        f"but trip is {nights} nights."
                    )

        # --- 6. Itinerary Feasibility (if provided) ---
        if itinerary_result and itinerary_result.data:
            days = itinerary_result.data.get("days", [])
            if len(days) < trip_days:
                issues.append(
                    f"Itinerary only covers {len(days)} days but trip is {trip_days + 1} days."
                )

        # --- Determine Overall Status ---
        if len(issues) > 0:
            validation_status = "FAIL"
            status = "warning"
        else:
            validation_status = "PASS"
            status = "success"

        return AgentResult(
            agent_name="VerificationAgent",
            status=status,
            data=ValidationResult(status=validation_status, issues=issues).model_dump(),
        )

    except Exception as e:
        logger.error(f"Verification Agent failed: {e}")
        return AgentResult(
            agent_name="VerificationAgent", status="error", errors=[str(e)]
        )
