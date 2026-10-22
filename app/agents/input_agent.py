from app.models.schemas import TripRequest
from app.utils.logger import logger


def run_input_agent(request: TripRequest) -> TripRequest:
    """
    Validates the incoming request and ensures logical constraints.
    Pydantic handles the heavy lifting, but this agent logs the normalization.
    """
    logger.info(f"Input Agent validating request for {request.destination}")

    # Example of a custom constraint check
    if request.budget_amount < 1000:
        logger.warning("Budget is suspiciously low. Flagging for verification.")

    return request
