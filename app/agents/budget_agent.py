from app.models.schemas import TripRequest, AgentResult, BudgetBreakdown
from app.tools.currency import get_exchange_rate
from app.utils.logger import logger


async def run_budget_agent(
    request: TripRequest,
    flight_result: AgentResult,
    stay_result: AgentResult,
    activity_result: AgentResult,
) -> AgentResult:
    """
    Deterministic Budget Agent.
    Calculates the total cost, converts currencies, and estimates daily expenses.
    """
    logger.info("Budget Agent running...")

    try:
        # 1. Extract base costs and currencies from the search results
        flights = flight_result.data or []
        stays = stay_result.data or []
        activities = activity_result.data or []

        # Assume the cheapest options are at index 0 (we sorted them in the mock tools)
        flight_cost = flights[0]["price"] if flights else 0.0
        flight_currency = flights[0]["currency"] if flights else request.budget_currency

        stay_cost = stays[0]["total_stay_cost"] if stays else 0.0
        stay_currency = stays[0]["currency"] if stays else request.budget_currency

        activity_cost = sum(a.get("cost", 0.0) for a in activities)
        # Assuming activities are in the same currency as stay/flight for this MVP
        activity_currency = stays[0]["currency"] if stays else request.budget_currency

        # 2. Convert everything to the user's requested budget currency
        flight_rate_data = await get_exchange_rate(
            flight_currency, request.budget_currency
        )
        stay_rate_data = await get_exchange_rate(stay_currency, request.budget_currency)

        flight_rate = flight_rate_data["rate"]
        stay_rate = stay_rate_data["rate"]

        flights_total = flight_cost * flight_rate
        stay_total = stay_cost * stay_rate
        activities_total = activity_cost * stay_rate

        # 3. Estimate Food, Transport, and Misc expenses (Deterministic Math)
        # Manual requires: "Estimate food, local transport, tickets and miscellaneous costs."
        days = max(1, (request.end_date - request.start_date).days)

        # Estimates in PKR (Baseline for the demo)
        # Assuming 5000 PKR per person per day for food, 2000 for transport
        food_est = 5000.0 * request.travelers * days
        transport_est = 2000.0 * request.travelers * days
        misc_est = 5000.0 * request.travelers  # Flat estimate for shopping/tips

        # 4. Calculate Totals
        grand_total = (
            flights_total
            + stay_total
            + activities_total
            + food_est
            + transport_est
            + misc_est
        )
        remaining = request.budget_amount - grand_total
        over_budget = max(0.0, grand_total - request.budget_amount)

        # 5. Build the structured breakdown
        breakdown = BudgetBreakdown(
            flights_total=round(flights_total, 2),
            stay_total=round(stay_total, 2),
            activities_total=round(activities_total, 2),
            food_estimate=round(food_est, 2),
            transport_estimate=round(transport_est, 2),
            misc_estimate=round(misc_est, 2),
            grand_total=round(grand_total, 2),
            remaining_budget=round(remaining, 2),
            over_budget_amount=round(over_budget, 2),
            currency=request.budget_currency,
        )

        # 6. Determine Status
        status = "warning" if over_budget > 0 else "success"
        warnings = (
            [f"Plan is over budget by {over_budget:,.2f} {request.budget_currency}"]
            if over_budget > 0
            else []
        )

        logger.info(
            f"Budget calculated. Total: {grand_total:,.2f} {request.budget_currency}"
        )

        return AgentResult(
            agent_name="BudgetAgent",
            status=status,
            data=breakdown.model_dump(),  # Return as dict for state storage
            warnings=warnings,
        )

    except Exception as e:
        logger.error(f"Budget Agent failed: {e}")
        return AgentResult(
            agent_name="BudgetAgent",
            status="error",
            errors=[f"Failed to calculate budget: {str(e)}"],
        )
