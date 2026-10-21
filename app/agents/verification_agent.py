from app.models.schemas import TripRequest, AgentResult, ValidationResult
from app.utils.logger import logger


async def run_verification_agent(
    request: TripRequest, budget_result: AgentResult
) -> AgentResult:
    logger.info("Verification Agent running...")

    issues = []
    status = "success"

    try:
        budget = budget_result.data
        if not budget:
            raise ValueError("No budget data provided to verification.")

        # Check 1: Over budget?
        if budget["over_budget_amount"] > 0:
            issues.append(
                f"Over budget by {budget['over_budget_amount']} {request.budget_currency}."
            )

        # Check 2: Are flights missing?
        # (This would be connected to the actual AgentResults in a full implementation)

        # Determine overall status
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
