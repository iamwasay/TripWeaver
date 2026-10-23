import asyncio
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from app.models.schemas import (
    TripRequest,
    TripState,
    AgentResult,
    FlightOption,
    StayOption,
    ActivityOption,
)
from app.utils.logger import logger

# Import all our agents
from app.agents.input_agent import run_input_agent
from app.agents.flight_agent import run_flight_agent
from app.agents.stay_agent import run_stay_agent
from app.agents.activities_agent import run_activities_agent
from app.agents.weather_agent import run_weather_agent
from app.agents.budget_agent import run_budget_agent
from app.agents.verification_agent import run_verification_agent
from app.agents.itinerary_agent import run_itinerary_agent
from app.agents.final_agent import run_final_agent


# --- LANGGRAPH STATE DEFINITION ---
class GraphState(TypedDict):
    request: TripRequest
    state: TripState
    retry_count: int
    flight_res: AgentResult
    stay_res: AgentResult
    act_res: AgentResult
    budget_res: AgentResult


# --- NODE FUNCTIONS ---
async def input_node(graph_state: GraphState):
    logger.info("Node: Input Validation")
    req = run_input_agent(graph_state["request"])
    return {"request": req, "retry_count": 0}


async def search_node(graph_state: GraphState):
    logger.info("Node: Search Agents")
    req = graph_state["request"]

    flight_res, stay_res, act_res, weather_res = await asyncio.gather(
        run_flight_agent(req),
        run_stay_agent(req),
        run_activities_agent(req),
        run_weather_agent(req),
    )

    if flight_res.data:
        flight_res.data = sorted(
            flight_res.data, key=lambda x: float(x.get("price", 0))
        )
    if stay_res.data:
        stay_res.data = sorted(
            stay_res.data, key=lambda x: float(x.get("total_stay_cost", 0))
        )

    new_state = graph_state["state"].model_copy(deep=True)

    new_state.search_results = {
        "flights": flight_res.data or [],
        "stays": stay_res.data or [],
        "activities": act_res.data or [],
    }

    if act_res.data:
        new_state.activities = [ActivityOption(**a) for a in act_res.data]

    new_state.weather = weather_res.data

    new_messages = list(new_state.agent_messages)
    new_messages.extend([flight_res, stay_res, act_res, weather_res])
    new_state.agent_messages = new_messages

    return {
        "flight_res": flight_res,
        "stay_res": stay_res,
        "act_res": act_res,
        "state": new_state,
    }


async def budget_node(graph_state: GraphState):
    logger.info(
        f"Node: Budget Calculation (Attempt {graph_state.get('retry_count', 0) + 1})"
    )
    req = graph_state["request"]

    f_res = graph_state["flight_res"]
    s_res = graph_state["stay_res"]
    retries = graph_state.get("retry_count", 0)

    selected_flight_dict = None
    selected_stay_dict = None

    if f_res.data:
        f_idx = min(retries, len(f_res.data) - 1)
        selected_flight_dict = f_res.data[f_idx]

    if s_res.data:
        s_idx = min(retries, len(s_res.data) - 1)
        selected_stay_dict = s_res.data[s_idx]

    temp_f_res = AgentResult(
        agent_name="FlightAgent",
        status=f_res.status,
        data=[selected_flight_dict] if selected_flight_dict else [],
    )
    temp_s_res = AgentResult(
        agent_name="StayAgent",
        status=s_res.status,
        data=[selected_stay_dict] if selected_stay_dict else [],
    )

    budget_res = await run_budget_agent(
        req, temp_f_res, temp_s_res, graph_state["act_res"]
    )

    new_state = graph_state["state"].model_copy(deep=True)

    if selected_flight_dict:
        new_state.selected_flight = FlightOption(**selected_flight_dict)
    if selected_stay_dict:
        new_state.selected_stay = StayOption(**selected_stay_dict)

    new_messages = list(new_state.agent_messages)
    new_messages.append(budget_res)
    new_state.agent_messages = new_messages

    return {"budget_res": budget_res, "state": new_state}


async def verify_node(graph_state: GraphState):
    """First verification: checks budget, flights, hotels BEFORE itinerary generation."""
    logger.info("Node: Verification (Pre-Itinerary)")
    req = graph_state["request"]
    val_res = await run_verification_agent(
        req,
        graph_state["budget_res"],
        graph_state["flight_res"],
        graph_state["stay_res"],
        # itinerary_result is None here — itinerary doesn't exist yet
    )

    new_state = graph_state["state"].model_copy(deep=True)
    new_state.validation = val_res.data
    new_state.budget = graph_state["budget_res"].data

    new_messages = list(new_state.agent_messages)
    new_messages.append(val_res)
    new_state.agent_messages = new_messages

    return {"state": new_state}


async def post_verify_node(graph_state: GraphState):
    """
    FIX for Issue 15: Second verification AFTER itinerary generation.
    This re-runs all checks with the itinerary available, so it can validate:
    - Itinerary covers the requested dates
    - Activities don't conflict with flight times
    - Daily schedules are feasible
    """
    logger.info("Node: Post-Itinerary Verification")
    req = graph_state["request"]

    # Wrap the itinerary data as an AgentResult so the verifier can inspect it
    itin_res = AgentResult(
        agent_name="Itinerary", data=graph_state["state"].itinerary, status="success"
    )

    val_res = await run_verification_agent(
        req,
        graph_state["budget_res"],
        graph_state["flight_res"],
        graph_state["stay_res"],
        itin_res,  # Pass itinerary for feasibility checks
    )

    new_state = graph_state["state"].model_copy(deep=True)
    new_state.validation = val_res.data  # Update with latest verification result

    # Replace the old VerificationAgent message with the new one
    # (so the final output reflects the post-itinerary check)
    new_messages = []
    for msg in new_state.agent_messages:
        if msg.agent_name == "VerificationAgent":
            new_messages.append(val_res)  # Replace with updated check
        else:
            new_messages.append(msg)

    # If no previous verification was found, just append
    if not any(m.agent_name == "VerificationAgent" for m in new_messages):
        new_messages.append(val_res)

    new_state.agent_messages = new_messages

    return {"state": new_state}


def route_after_verification(graph_state: GraphState) -> Literal["revise", "itinerary"]:
    # If a core API failed (e.g., SerpApi is down), do NOT try to revise.
    if (
        graph_state["flight_res"].status == "error"
        or graph_state["stay_res"].status == "error"
    ):
        logger.warning(
            "Core API failure detected. Stopping revision loop to prevent misleading retries."
        )
        return "itinerary"

    if graph_state["state"].validation["status"] != "FAIL":
        return "itinerary"

    if graph_state.get("retry_count", 0) >= 2:
        logger.warning("Max retries reached. Stopping revision loop.")
        return "itinerary"

    f_len = len(graph_state["flight_res"].data) if graph_state["flight_res"].data else 0
    s_len = len(graph_state["stay_res"].data) if graph_state["stay_res"].data else 0
    max_options = max(f_len, s_len)

    if graph_state.get("retry_count", 0) + 1 >= max_options:
        logger.warning(
            "No more cheaper alternatives available. Stopping revision loop."
        )
        return "itinerary"

    logger.warning("Verification FAILED. Routing back to Budget for cheaper options.")
    return "revise"


async def revise_node(graph_state: GraphState):
    return {"retry_count": graph_state.get("retry_count", 0) + 1}


async def itinerary_node(graph_state: GraphState):
    logger.info("Node: Itinerary Generation")
    req = graph_state["request"]
    itin_res = await run_itinerary_agent(
        req,
        graph_state["act_res"],
        graph_state["flight_res"],
        AgentResult(agent_name="Validation", data=graph_state["state"].validation),
    )

    new_state = graph_state["state"].model_copy(deep=True)
    new_state.itinerary = itin_res.data

    new_messages = list(new_state.agent_messages)
    new_messages.append(itin_res)
    new_state.agent_messages = new_messages

    return {"state": new_state}


async def final_node(graph_state: GraphState):
    logger.info("Node: Final Response")
    req = graph_state["request"]
    final_res = await run_final_agent(
        req,
        graph_state["budget_res"],
        AgentResult(agent_name="Itinerary", data=graph_state["state"].itinerary),
        AgentResult(agent_name="Validation", data=graph_state["state"].validation),
        graph_state["state"].agent_messages,  # Pass all agent messages
    )

    new_state = graph_state["state"].model_copy(deep=True)

    new_messages = list(new_state.agent_messages)
    new_messages.append(final_res)
    new_state.agent_messages = new_messages

    return {"state": new_state}


# --- BUILD THE LANGGRAPH ---
workflow = StateGraph(GraphState)

workflow.add_node("input", input_node)
workflow.add_node("search", search_node)
workflow.add_node("budget", budget_node)
workflow.add_node("verify", verify_node)
workflow.add_node("revise", revise_node)
workflow.add_node("itinerary", itinerary_node)
workflow.add_node("post_verify", post_verify_node)  # NEW NODE
workflow.add_node("final", final_node)

workflow.set_entry_point("input")
workflow.add_edge("input", "search")
workflow.add_edge("search", "budget")
workflow.add_edge("budget", "verify")

workflow.add_conditional_edges(
    "verify", route_after_verification, {"revise": "revise", "itinerary": "itinerary"}
)
workflow.add_edge("revise", "budget")
workflow.add_edge("itinerary", "post_verify")  # CHANGED: was "final"
workflow.add_edge("post_verify", "final")  # NEW
workflow.add_edge("final", END)

app_graph = workflow.compile()


# --- MAIN ENTRY POINT ---
async def orchestrate_trip(request: TripRequest) -> TripState:
    initial_state = {
        "request": request,
        "state": TripState(trip_request=request),
        "retry_count": 0,
    }
    logger.info("=== LANGGRAPH ORCHESTRATOR STARTED ===")
    final_output = await app_graph.ainvoke(initial_state)
    logger.info("=== LANGGRAPH ORCHESTRATOR COMPLETED ===")
    return final_output["state"]
