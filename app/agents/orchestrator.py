import asyncio
from app.models.schemas import TripRequest, TripState, AgentResult
from app.utils.logger import logger

# Import all our agents
from app.agents.flight_agent import run_flight_agent
from app.agents.stay_agent import run_stay_agent
from app.agents.activities_agent import run_activities_agent
from app.agents.weather_agent import run_weather_agent
from app.agents.budget_agent import run_budget_agent
from app.agents.verification_agent import run_verification_agent
from app.agents.itinerary_agent import run_itinerary_agent
from app.agents.final_agent import run_final_agent


async def orchestrate_trip(request: TripRequest) -> TripState:
    """
    The Orchestrator coordinates the entire workflow.
    """
    logger.info("=== ORCHESTRATOR STARTED ===")
    state = TripState(trip_request=request)

    # 1. Run Search Agents in Parallel (as required by the manual)
    logger.info("Dispatching parallel search agents...")
    flight_res, stay_res, act_res, weather_res = await asyncio.gather(
        run_flight_agent(request),
        run_stay_agent(request),
        run_activities_agent(request),
        run_weather_agent(request),
    )

    # Save to state
    state.agent_messages.extend([flight_res, stay_res, act_res, weather_res])
    state.weather = weather_res.data

    # 2. Run Budget Agent
    logger.info("Calculating budget...")
    budget_res = await run_budget_agent(request, flight_res, stay_res, act_res)
    state.agent_messages.append(budget_res)
    state.budget = budget_res.data

    # 3. Run Verification Agent
    logger.info("Verifying constraints...")
    val_res = await run_verification_agent(request, budget_res)
    state.agent_messages.append(val_res)
    state.validation = val_res.data

    # 4. Run Itinerary Agent
    logger.info("Building itinerary...")
    itinerary_res = await run_itinerary_agent(request, act_res)
    state.agent_messages.append(itinerary_res)
    state.itinerary = itinerary_res.data

    # 5. Run Final Response Agent
    logger.info("Generating final response...")
    final_res = await run_final_agent(request, budget_res, itinerary_res, val_res)
    state.agent_messages.append(final_res)

    logger.info("=== ORCHESTRATOR COMPLETE ===")

    # We add the final human-readable text to the state
    state.trip_request = request  # ensure it's saved
    return state
