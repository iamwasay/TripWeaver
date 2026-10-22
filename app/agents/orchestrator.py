import asyncio
from typing import TypedDict, Literal
from langgraph.graph import StateGraph, END
from app.models.schemas import TripRequest, TripState, AgentResult
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
    logger.info(
        f"Node: Search Agents (Attempt {graph_state.get('retry_count', 0) + 1})"
    )
    req = graph_state["request"]

    flight_res, stay_res, act_res, weather_res = await asyncio.gather(
        run_flight_agent(req),
        run_stay_agent(req),
        run_activities_agent(req),
        run_weather_agent(req),
    )
    graph_state["state"].weather = weather_res.data
    return {"flight_res": flight_res, "stay_res": stay_res, "act_res": act_res}


async def budget_node(graph_state: GraphState):
    logger.info("Node: Budget Calculation")
    req = graph_state["request"]

    f_res = graph_state["flight_res"]
    s_res = graph_state["stay_res"]
    retries = graph_state.get("retry_count", 0)

    # FIX: Sort flights and hotels by price ascending before attempting revision
    if f_res.data:
        f_res.data = sorted(f_res.data, key=lambda x: float(x.get("price", 0)))
    if s_res.data:
        s_res.data = sorted(
            s_res.data, key=lambda x: float(x.get("total_stay_cost", 0))
        )

    # REVISION LOOP: If retry_count > 0, swap to the next cheapest option
    if retries > 0 and len(f_res.data) > retries:
        logger.warning(f"Revision Loop: Swapping to flight option index {retries}")
        f_res.data = [f_res.data[retries]]  # Keep only the next cheapest

    if retries > 0 and len(s_res.data) > retries:
        logger.warning(f"Revision Loop: Swapping to hotel option index {retries}")
        s_res.data = [s_res.data[retries]]

    budget_res = await run_budget_agent(req, f_res, s_res, graph_state["act_res"])
    return {"budget_res": budget_res}


async def verify_node(graph_state: GraphState):
    logger.info("Node: Verification")
    req = graph_state["request"]
    val_res = await run_verification_agent(req, graph_state["budget_res"])
    graph_state["state"].validation = val_res.data
    graph_state["state"].budget = graph_state["budget_res"].data
    return {"state": graph_state["state"]}


def route_after_verification(graph_state: GraphState) -> Literal["revise", "itinerary"]:
    # If FAIL and we haven't tried 3 times, loop back to revise!
    if (
        graph_state["state"].validation["status"] == "FAIL"
        and graph_state.get("retry_count", 0) < 2
    ):
        logger.warning(
            "Verification FAILED. Routing back to Search for cheaper options."
        )
        return "revise"
    return "itinerary"


async def revise_node(graph_state: GraphState):
    return {"retry_count": graph_state.get("retry_count", 0) + 1}


async def itinerary_node(graph_state: GraphState):
    logger.info("Node: Itinerary Generation")
    req = graph_state["request"]
    itin_res = await run_itinerary_agent(req, graph_state["act_res"])
    graph_state["state"].itinerary = itin_res.data
    return {"state": graph_state["state"]}


async def final_node(graph_state: GraphState):
    logger.info("Node: Final Response")
    req = graph_state["request"]
    final_res = await run_final_agent(
        req,
        graph_state["budget_res"],
        AgentResult(agent_name="Itinerary", data=graph_state["state"].itinerary),
        AgentResult(agent_name="Validation", data=graph_state["state"].validation),
    )
    graph_state["state"].agent_messages.append(final_res)
    return {"state": graph_state["state"]}


# --- BUILD THE LANGGRAPH ---
workflow = StateGraph(GraphState)

workflow.add_node("input", input_node)
workflow.add_node("search", search_node)
workflow.add_node("budget", budget_node)
workflow.add_node("verify", verify_node)
workflow.add_node("revise", revise_node)
workflow.add_node("itinerary", itinerary_node)
workflow.add_node("final", final_node)

workflow.set_entry_point("input")
workflow.add_edge("input", "search")
workflow.add_edge("search", "budget")
workflow.add_edge("budget", "verify")

# Conditional edge for revision loop
workflow.add_conditional_edges(
    "verify", route_after_verification, {"revise": "revise", "itinerary": "itinerary"}
)
workflow.add_edge("revise", "budget")  # Loop back to budget with new (cheaper) options
workflow.add_edge("itinerary", "final")
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
    logger.info("=== LANGGRAPH ORCHESTRATOR COMPLETE ===")
    return final_output["state"]
