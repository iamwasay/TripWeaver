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
    Calculates the total cost, converts currencies properly, and estimates daily expenses.
    """
    logger.info("Budget Agent running...")

    try:
        # 1. Extract base costs
        flights = flight_result.data or []
        stays = stay_result.data or []
        activities = activity_result.data or []

        # Fail early if critical components are missing
        if not flights:
            raise ValueError("No flights available to calculate budget.")
        if not stays:
            raise ValueError("No stays available to calculate budget.")

        # --- FLIGHTS ---
        flight_cost = flights[0].get("price", 0.0)
        flight_currency = flights[0].get("currency", "USD")
        flight_rate_data = await get_exchange_rate(
            flight_currency, request.budget_currency
        )
        flights_total = flight_cost * flight_rate_data["rate"]

        # --- STAYS ---
        stay_cost = stays[0].get("total_stay_cost", 0.0)
        stay_currency = stays[0].get("currency", "USD")
        stay_rate_data = await get_exchange_rate(stay_currency, request.budget_currency)
        stay_total = stay_cost * stay_rate_data["rate"]

        # --- ACTIVITIES ---
        # Perfect Fix for Issue 1: Convert EACH activity from its own currency
        activities_total = 0.0
        has_estimated_activities = False

        for act in activities:
            act_cost = act.get("cost", 0.0)
            act_currency = act.get("currency", "USD")
            if act.get("is_estimated", True):
                has_estimated_activities = True

            if act_cost > 0:
                act_rate_data = await get_exchange_rate(
                    act_currency, request.budget_currency
                )
                activities_total += act_cost * act_rate_data["rate"]

        # --- ESTIMATES (FOOD, TRANSPORT, MISC) ---
        # Base estimates in USD, then convert to the user's budget currency
        days = max(1, (request.end_date - request.start_date).days)

        BASE_FOOD_USD = 25.0
        BASE_TRANSPORT_USD = 10.0
        BASE_MISC_USD = 20.0

        usd_rate_data = await get_exchange_rate("USD", request.budget_currency)
        usd_rate = usd_rate_data["rate"]

        food_est = BASE_FOOD_USD * request.travelers * days * usd_rate
        transport_est = BASE_TRANSPORT_USD * request.travelers * days * usd_rate
        misc_est = BASE_MISC_USD * request.travelers * usd_rate

        # --- CALCULATE TOTALS ---
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

        status = "warning" if over_budget > 0 else "success"
        warnings = []

        if over_budget > 0:
            warnings.append(
                f"Plan is over budget by {over_budget:,.2f} {request.budget_currency}"
            )

        if has_estimated_activities:
            warnings.append(
                "Some activity costs are estimates and may vary from the actual ticket price."
            )

        logger.info(
            f"Budget calculated. Total: {grand_total:,.2f} {request.budget_currency}"
        )

        return AgentResult(
            agent_name="BudgetAgent",
            status=status,
            data=breakdown.model_dump(),
            warnings=warnings,
        )

    except Exception as e:
        logger.error(f"Budget Agent failed: {e}")
        return AgentResult(
            agent_name="BudgetAgent",
            status="error",
            errors=[f"Failed to calculate budget: {str(e)}"],
        )
