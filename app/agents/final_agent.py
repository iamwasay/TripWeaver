from app.models.schemas import TripRequest, AgentResult
from app.utils.logger import logger


async def run_final_agent(
    request: TripRequest,
    budget_result: AgentResult,
    itinerary_result: AgentResult,
    validation_result: AgentResult,
) -> AgentResult:
    logger.info("Final Response Agent running...")

    try:
        budget = budget_result.data
        itinerary = itinerary_result.data
        validation = validation_result.data

        summary = f"Trip to {request.destination}\n"
        summary += f"Budget: {request.budget_amount} {request.budget_currency}\n"
        summary += (
            f"Total Estimated Cost: {budget['grand_total']} {request.budget_currency}\n"
        )
        summary += (
            f"Remaining: {budget['remaining_budget']} {request.budget_currency}\n\n"
        )

        if validation["status"] == "FAIL":
            summary += "⚠️ WARNING: This plan is over budget!\n"
            for issue in validation["issues"]:
                summary += f"- {issue}\n"
        else:
            summary += "✅ Plan is within budget.\n"

        summary += f"\nItinerary: {len(itinerary['days'])} days planned."

        return AgentResult(
            agent_name="FinalAgent",
            status="success",
            data={"summary": summary, "raw_budget": budget, "raw_itinerary": itinerary},
        )
    except Exception as e:
        logger.error(f"Final Agent failed: {e}")
        return AgentResult(agent_name="FinalAgent", status="error", errors=[str(e)])
