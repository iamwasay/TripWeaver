from app.models.schemas import TripRequest, AgentResult
from app.utils.logger import logger


async def run_final_agent(
    request: TripRequest,
    budget_result: AgentResult,
    itinerary_result: AgentResult,
    validation_result: AgentResult,
    agent_messages: list = None,
) -> AgentResult:
    logger.info("Final Response Agent running...")

    try:
        budget = budget_result.data or {}
        itinerary = itinerary_result.data or {}
        validation = validation_result.data or {}

        summary = f"Trip to {request.destination}\n"
        summary += f"Budget: {request.budget_amount} {request.budget_currency}\n"

        if budget:
            summary += f"Total Estimated Cost: {budget.get('grand_total', 0)} {request.budget_currency}\n"
            summary += f"Remaining: {budget.get('remaining_budget', 0)} {request.budget_currency}\n\n"

        if validation.get("status") == "FAIL":
            summary += "⚠️ WARNING: This plan could not be fully verified:\n"
            for issue in validation.get("issues", []):
                summary += f"- {issue}\n"
        else:
            summary += "✅ Plan is within budget and verified.\n"

        summary += f"\nItinerary: {len(itinerary.get('days', []))} days planned.\n"

        # Collect all warnings and errors from all agents
        all_warnings = []
        if agent_messages:
            for msg in agent_messages:
                if msg.warnings:
                    for w in msg.warnings:
                        all_warnings.append(f"[{msg.agent_name}] {w}")
                if msg.errors:
                    for e in msg.errors:
                        all_warnings.append(f"[{msg.agent_name} Error] {e}")

        if all_warnings:
            summary += "\nData Quality Notes:\n"
            for w in dict.fromkeys(all_warnings):  # Deduplicate preserving order
                summary += f"- {w}\n"

        return AgentResult(
            agent_name="FinalAgent",
            status="success",
            data={"summary": summary, "raw_budget": budget, "raw_itinerary": itinerary},
        )
    except Exception as e:
        logger.error(f"Final Agent failed: {e}")
        return AgentResult(agent_name="FinalAgent", status="error", errors=[str(e)])
