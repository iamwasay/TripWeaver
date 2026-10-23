from app.models.schemas import TripRequest, AgentResult, ValidationResult
from app.utils.logger import logger


async def run_verification_agent(
    request: TripRequest,
    budget_result: AgentResult,
    flight_result: AgentResult,
    stay_result: AgentResult,
) -> AgentResult:
    logger.info("Verification Agent running...")

    issues = []
    status = "success"

    try:
        # 1. Check Budget
        budget = budget_result.data
        if not budget:
            issues.append("Budget calculation failed.")
        elif budget.get("over_budget_amount", 0) > 0:
            issues.append(
                f"Over budget by {budget['over_budget_amount']:,.2f} {request.budget_currency}."
            )

        # 2. Check Missing Flights
        if not flight_result.data or flight_result.status == "error":
            issues.append("No valid flights were found for this route.")

        # 3. Check Missing Hotels
        if not stay_result.data or stay_result.status == "error":
            issues.append("No valid hotels were found for these dates.")

        # 4. Determine overall status
        if len(issues) > 0:
            validation_status = "FAIL"
            status = "warning"
        else:
            validation_status = "PASS"

        validation_result = ValidationResult(status=validation_status, issues=issues)

        return AgentResult(
            agent_name="VerificationAgent",
            status=status,
            data=validation_result.model_dump(),
        )

    except Exception as e:
        logger.error(f"Verification Agent failed: {e}")
        return AgentResult(
            agent_name="VerificationAgent", status="error", errors=[str(e)]
        )
