import os
import certifi
from dotenv import load_dotenv

load_dotenv()
os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

# LangSmith Observability setup
_ls_key = os.getenv("LANGCHAIN_API_KEY") or os.getenv("LANGSMITH_API_KEY")
if _ls_key:
    os.environ["LANGCHAIN_TRACING_V2"] = "true"
    os.environ["LANGCHAIN_API_KEY"] = _ls_key.strip('"').strip("'")
    os.environ["LANGCHAIN_PROJECT"] = (os.getenv("LANGCHAIN_PROJECT") or os.getenv("LANGSMITH_PROJECT") or "Tripmate-AI").strip('"').strip("'")
    os.environ["LANGCHAIN_ENDPOINT"] = "https://api.smith.langchain.com"


from typing import Any, TypedDict, Annotated
import operator
import uuid
import asyncio
import json
import psycopg
from psycopg.rows import dict_row
from langgraph.graph import StateGraph, START, END
from langgraph.checkpoint.postgres import PostgresSaver
from langgraph.types import Command, interrupt
from langchain_core.messages import (
    AnyMessage,
    HumanMessage,
    AIMessage,
    SystemMessage,
)
from langchain_groq import ChatGroq

from mcp_client import (
    tavily_mcp_search,
    aviation_mcp_call,
    extract_destination,
    forecast_mcp_search,
    weather_mcp_search,
    get_groq_llm,
)


def get_database_url() -> str:
    database_url = os.getenv("DATABASE_URL")
    if not database_url:
        raise ValueError("DATABASE_URL is missing. Please add your PostgreSQL connection URL to .env")

    if "sslmode=" not in database_url:
        separator = "&" if "?" in database_url else "?"
        database_url = f"{database_url}{separator}sslmode=require"

    return database_url


llm = get_groq_llm()


# =========================
# State Definition
# =========================
class TravelState(TypedDict, total=False):
    messages: Annotated[list[AnyMessage], operator.add]
    user_query: str

    # Supervisor + guardrail state
    guardrail_allowed: bool
    guardrail_reason: str
    selected_agents: list[str]
    trip_constraints: dict[str, Any]
    supervisor_reasoning: str

    # Specialist results
    flight_results: str
    hotel_results: str
    weather_results: str
    budget_results: str
    itinerary: str

    # Human-In-The-Loop approval state
    approval_request: str
    approved: bool
    human_feedback: str
    final_response: str

    llm_calls: int


KNOWN_AGENTS = {
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
}

AGENT_ORDER = [
    "flight_agent",
    "hotel_agent",
    "weather_agent",
    "budget_agent",
    "itinerary_agent",
]


def _llm_text(system_prompt: str, user_prompt: str) -> str:
    response = llm.invoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    return str(response.content)


def _json_from_llm(text: str) -> dict[str, Any]:
    """Extract the first complete JSON object returned by the model."""
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end < start:
        raise ValueError("The model did not return a JSON object.")
    return json.loads(text[start : end + 1])


def _empty_constraints() -> dict[str, Any]:
    return {
        "destination": "",
        "origin": "",
        "duration": "",
        "budget": "",
        "travel_style": "",
        "special_preferences": [],
    }


# =========================
# Supervisor Agent + Input Guardrail
# =========================
def supervisor_agent(state: TravelState):
    query = state["user_query"]
    llm_calls = state.get("llm_calls", 0)

    guardrail_prompt = f"""
Determine whether the following request belongs to travel planning or travel
information. Valid requests include destinations, flights, hotels, weather,
budgets, visas, transportation, sightseeing, food, packing, or itineraries.

Block clearly unrelated requests and requests asking for harmful or illegal
instructions. Do not block a valid travel request merely because some details
are missing.

Return strict JSON only:
{{
  "allowed": true,
  "reason": ""
}}

User request:
{query}
"""

    try:
        guardrail_raw = _llm_text(
            "You are the input guardrail for a travel-planning application. Return strict JSON only.",
            guardrail_prompt,
        )
        guardrail_result = _json_from_llm(guardrail_raw)
        allowed = bool(guardrail_result.get("allowed", True))
        guardrail_reason = str(guardrail_result.get("reason", "")).strip()
        llm_calls += 1
    except Exception as exc:
        print(f"Guardrail fallback used: {exc}")
        allowed = True
        guardrail_reason = "Guardrail validation fallback allowed the request."

    if not allowed:
        reason = guardrail_reason or (
            "TripMate AI can only help with travel-planning requests. "
            "Please ask about a destination, flight, hotel, weather, budget, "
            "or itinerary."
        )
        return {
            "guardrail_allowed": False,
            "guardrail_reason": reason,
            "selected_agents": [],
            "trip_constraints": _empty_constraints(),
            "supervisor_reasoning": reason,
            "final_response": reason,
            "messages": [AIMessage(content=f"Guardrail blocked request: {reason}")],
            "llm_calls": llm_calls,
        }

    supervisor_prompt = f"""
You are the supervisor of a multi-agent travel-planning system.
Choose only the specialist agents needed for the request.

Available agents:
- flight_agent: flights, airports, airlines, routes, airfare, or booking advice
- hotel_agent: hotels, accommodation, neighborhoods, or places to stay
- weather_agent: weather, climate, season, forecast, or packing advice
- budget_agent: cost, affordability, price limits, or budget feasibility
- itinerary_agent: creates the integrated travel plan and must always be included

Return strict JSON only using this schema:
{{
  "selected_agents": ["flight_agent", "hotel_agent", "weather_agent", "budget_agent", "itinerary_agent"],
  "trip_constraints": {{
    "destination": "",
    "origin": "",
    "duration": "",
    "budget": "",
    "travel_style": "",
    "special_preferences": []
  }},
  "reasoning": ""
}}

User request:
{query}
"""

    try:
        supervisor_raw = _llm_text(
            "You route work to travel specialist agents. Return strict JSON only.",
            supervisor_prompt,
        )
        parsed = _json_from_llm(supervisor_raw)
        requested_agents = parsed.get("selected_agents", [])
        selected_agents = [
            name for name in AGENT_ORDER if name in requested_agents and name in KNOWN_AGENTS
        ]

        if "itinerary_agent" not in selected_agents:
            selected_agents.append("itinerary_agent")

        constraints = _empty_constraints()
        parsed_constraints = parsed.get("trip_constraints", {})
        if isinstance(parsed_constraints, dict):
            constraints.update(parsed_constraints)

        reasoning = str(parsed.get("reasoning", "")).strip()
        llm_calls += 1
    except Exception as exc:
        print(f"Supervisor fallback used: {exc}")
        selected_agents = AGENT_ORDER.copy()
        constraints = _empty_constraints()
        reasoning = "Supervisor routing fallback selected all specialist agents."

    return {
        "guardrail_allowed": True,
        "guardrail_reason": guardrail_reason,
        "selected_agents": selected_agents,
        "trip_constraints": constraints,
        "supervisor_reasoning": reasoning,
        "messages": [AIMessage(content="Supervisor prepared execution plan.")],
        "llm_calls": llm_calls,
    }


def guardrail_blocked_agent(state: TravelState):
    reason = state.get("final_response") or state.get("guardrail_reason") or (
        "This request was blocked by the travel input guardrail."
    )
    return {
        "final_response": reason,
        "messages": [AIMessage(content=reason)],
    }


# =========================
# Flight Agent
# =========================
FLIGHT_AGENT_PROMPT = """
You are an expert flight specialist.

User Query:
{query}

Airport / Flight Data:
{flight_data}

Generate:
1. Likely departure and arrival airports
2. Airlines operating this route
3. Typical flight duration and transit considerations
4. Estimated airfare range
5. High/low season pricing notes
6. Booking strategy and tips

Return clear, concise guidance.
"""


def flight_agent(state: TravelState):
    query = state["user_query"]
    try:
        airports = asyncio.run(aviation_mcp_call("list_airports"))
        airlines = asyncio.run(aviation_mcp_call("list_airlines"))
        flight_data = f"Airports:\n{str(airports)[:1500]}\nAirlines:\n{str(airlines)[:1500]}"
    except Exception as exc:
        flight_data = f"Flight details estimated: {exc}"

    prompt = FLIGHT_AGENT_PROMPT.format(query=query, flight_data=flight_data)
    response = llm.invoke(
        [
            SystemMessage(content="You are an expert flight planner."),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "flight_results": str(response.content),
        "messages": [AIMessage(content="Flight information generated.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Hotel Agent
# =========================
def hotel_agent(state: TravelState):
    query = f"Best hotels and places to stay for {state['user_query']}"
    try:
        hotel_results = asyncio.run(tavily_mcp_search(query))
    except Exception as exc:
        hotel_results = (
            "Recommended neighborhoods and lodging options based on standard travel tiers: "
            "Luxury, Mid-range boutique, and Budget hostels."
        )

    return {
        "hotel_results": str(hotel_results),
        "messages": [AIMessage(content="Hotel recommendations processed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Weather Agent
# =========================
def weather_agent(state: TravelState):
    city = extract_destination(state["user_query"])
    try:
        current = asyncio.run(weather_mcp_search(city))
        forecast = asyncio.run(forecast_mcp_search(city))
        weather_results = f"Current Weather in {city}:\n{current}\n\nForecast:\n{forecast}"
    except Exception as exc:
        weather_results = f"Weather data for {city}: Typical seasonal conditions with packing advice."

    return {
        "weather_results": weather_results,
        "messages": [AIMessage(content="Weather data processed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Budget Agent
# =========================
def budget_agent(state: TravelState):
    prompt = f"""
Analyze the overall financial feasibility of this trip.

User Query:
{state['user_query']}

Trip Constraints:
{state.get('trip_constraints', {})}

Flight Insights:
{state.get('flight_results', '')[:1000]}

Hotel Insights:
{state.get('hotel_results', '')[:1000]}

Provide:
1. Estimated Cost Breakdown (Flights, Accommodation, Food, Activities, Local Transit)
2. Budget Risk Areas (hidden costs, peak season markups)
3. Money-Saving Recommendations
4. Feasibility Verdict

Keep it practical and realistic.
"""
    response = llm.invoke(
        [
            SystemMessage(content="You are a practical travel budget analyst."),
            HumanMessage(content=prompt),
        ]
    )

    return {
        "budget_results": str(response.content),
        "messages": [AIMessage(content="Budget feasibility analysis completed.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Itinerary Agent
# =========================
def itinerary_agent(state: TravelState):
    prompt = f"""
Create a comprehensive, cohesive day-by-day travel itinerary draft based on the collected specialist information.

User Request:
{state['user_query']}

Trip Constraints:
{state.get('trip_constraints', {})}

Flight Details:
{state.get('flight_results', '')[:1500]}

Hotel Suggestions:
{state.get('hotel_results', '')[:1500]}

Weather Considerations:
{state.get('weather_results', '')[:1500]}

Budget Guidelines:
{state.get('budget_results', '')[:1500]}

Format with clear daily schedules, top sights, meal recommendations, and local travel tips.
Produce a high quality draft ready for traveler review.
"""
    response = llm.invoke(
        [
            SystemMessage(content="You are a senior travel itinerary designer."),
            HumanMessage(content=prompt),
        ]
    )

    approval_request = (
        "Please review the generated draft itinerary below. You can approve it to finalize "
        "or request specific revisions (e.g., adjust budget, change hotel preferences, add free time)."
    )

    return {
        "itinerary": str(response.content),
        "approval_request": approval_request,
        "messages": [AIMessage(content="Draft itinerary generated for traveler review.")],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Human-in-the-Loop (HITL) Node
# =========================
def human_approval_agent(state: TravelState):
    # LangGraph interrupt pauses thread execution until resumed by client
    review = interrupt(
        {
            "question": "Do you approve this draft itinerary?",
            "draft_itinerary": state.get("itinerary", ""),
            "approval_request": state.get("approval_request", ""),
            "selected_agents": state.get("selected_agents", []),
            "supervisor_reasoning": state.get("supervisor_reasoning", ""),
            "expected_response": {
                "approved": True,
                "feedback": "Optional revision feedback",
            },
        }
    )

    approved = bool(review.get("approved", False))
    human_feedback = str(review.get("feedback", "")).strip()

    return {
        "approved": approved,
        "human_feedback": human_feedback,
        "messages": [AIMessage(content="Human approval step processed.")],
    }


# =========================
# Final Agent
# =========================
def final_agent(state: TravelState):
    approved = state.get("approved", False)
    human_feedback = state.get("human_feedback", "").strip()

    if approved:
        review_guidance = "The user approved the draft. Polish and finalize it into an exceptional itinerary."
    else:
        review_guidance = f"The user requested revisions with feedback: '{human_feedback}'. Incorporate these adjustments thoroughly."

    final_prompt = f"""
Generate the complete final travel master plan for the user.

Traveler Feedback / Review:
{review_guidance}

Original Request:
{state['user_query']}

Flights:
{state.get('flight_results', '')[:1000]}

Hotels:
{state.get('hotel_results', '')[:1000]}

Weather:
{state.get('weather_results', '')[:1000]}

Budget:
{state.get('budget_results', '')[:1000]}

Draft Itinerary:
{state.get('itinerary', '')}

Format the final response cleanly with markdown using these exact sections:
# ✈️ TripMate AI Master Travel Plan

### 1. Trip Overview & Summary
### 2. Flight & Arrival Information
### 3. Recommended Accommodation
### 4. Weather & Packing Guidance
### 5. Day-by-Day Detailed Itinerary
### 6. Budget Breakdown & Estimates
### 7. Essential Travel Tips & Recommendations
"""

    response = llm.invoke(
        [
            SystemMessage(content="You are a professional AI travel booking and concierge assistant."),
            HumanMessage(content=final_prompt),
        ]
    )

    return {
        "final_response": str(response.content),
        "messages": [response],
        "llm_calls": state.get("llm_calls", 0) + 1,
    }


# =========================
# Dynamic Routing Logic
# =========================
ROUTE_MAP = {
    "guardrail_blocked": "guardrail_blocked",
    "flight_agent": "flight_agent",
    "hotel_agent": "hotel_agent",
    "weather_agent": "weather_agent",
    "budget_agent": "budget_agent",
    "itinerary_agent": "itinerary_agent",
}


def _selected_agents(state: TravelState) -> list[str]:
    selected = state.get("selected_agents", [])
    return [agent for agent in AGENT_ORDER if agent in selected]


def route_from_supervisor(state: TravelState) -> str:
    if not state.get("guardrail_allowed", True):
        return "guardrail_blocked"

    selected = _selected_agents(state)
    return selected[0] if selected else "itinerary_agent"


def route_after_agent(current_agent: str):
    def route(state: TravelState) -> str:
        selected = _selected_agents(state)
        current_index = AGENT_ORDER.index(current_agent)

        for next_agent in AGENT_ORDER[current_index + 1 :]:
            if next_agent in selected:
                return next_agent

        return "itinerary_agent"

    return route


# =========================
# StateGraph Construction
# =========================
graph = StateGraph(TravelState)

graph.add_node("supervisor", supervisor_agent)
graph.add_node("guardrail_blocked", guardrail_blocked_agent)
graph.add_node("flight_agent", flight_agent)
graph.add_node("hotel_agent", hotel_agent)
graph.add_node("weather_agent", weather_agent)
graph.add_node("budget_agent", budget_agent)
graph.add_node("itinerary_agent", itinerary_agent)
graph.add_node("human_approval", human_approval_agent)
graph.add_node("final_agent", final_agent)

graph.add_edge(START, "supervisor")
graph.add_conditional_edges("supervisor", route_from_supervisor, ROUTE_MAP)
graph.add_conditional_edges("flight_agent", route_after_agent("flight_agent"), ROUTE_MAP)
graph.add_conditional_edges("hotel_agent", route_after_agent("hotel_agent"), ROUTE_MAP)
graph.add_conditional_edges("weather_agent", route_after_agent("weather_agent"), ROUTE_MAP)
graph.add_conditional_edges("budget_agent", route_after_agent("budget_agent"), ROUTE_MAP)

graph.add_edge("itinerary_agent", "human_approval")
graph.add_edge("human_approval", "final_agent")
graph.add_edge("final_agent", END)
graph.add_edge("guardrail_blocked", END)

# PostgreSQL Connection Pool Checkpointer
from psycopg_pool import ConnectionPool

DATABASE_URL = get_database_url()
db_pool = ConnectionPool(
    conninfo=DATABASE_URL,
    min_size=1,
    max_size=10,
    check=ConnectionPool.check_connection,
    kwargs={"autocommit": True, "row_factory": dict_row, "prepare_threshold": 0},
)
db_pool.open()

checkpointer = PostgresSaver(db_pool)
checkpointer.setup()

travel_graph = graph.compile(checkpointer=checkpointer)


# =========================
# API-facing Execution Helpers
# =========================
def _interrupt_payload(result: dict[str, Any]) -> dict[str, Any] | None:
    interrupts = result.get("__interrupt__", [])
    if not interrupts:
        return None
    first = interrupts[0]
    payload = getattr(first, "value", first)
    return payload if isinstance(payload, dict) else {"value": payload}


def _serialize_result(result: dict[str, Any], thread_id: str) -> dict[str, Any]:
    messages = result.get("messages", [])
    last_message = messages[-1].content if messages else ""
    answer = result.get("final_response") or last_message
    interrupt_payload = _interrupt_payload(result)

    if interrupt_payload:
        answer = interrupt_payload.get("draft_itinerary") or result.get("itinerary", "")

    return {
        "thread_id": thread_id,
        "answer": answer,
        "requires_approval": interrupt_payload is not None,
        "approval_request": (
            interrupt_payload.get("approval_request", "")
            if interrupt_payload
            else result.get("approval_request", "")
        ),
        "flight_results": result.get("flight_results", ""),
        "hotel_results": result.get("hotel_results", ""),
        "weather_results": result.get("weather_results", ""),
        "budget_results": result.get("budget_results", ""),
        "itinerary": (
            interrupt_payload.get("draft_itinerary", "")
            if interrupt_payload
            else result.get("itinerary", "")
        ),
        "selected_agents": result.get("selected_agents", []),
        "trip_constraints": result.get("trip_constraints", {}),
        "supervisor_reasoning": result.get("supervisor_reasoning", ""),
        "guardrail_allowed": result.get("guardrail_allowed", True),
        "guardrail_reason": result.get("guardrail_reason", ""),
        "approved": result.get("approved"),
        "human_feedback": result.get("human_feedback", ""),
        "llm_calls": result.get("llm_calls", 0),
    }


def run_travel_agent(user_input: str, thread_id: str | None = None) -> dict[str, Any]:
    """Start a new travel planning thread and pause at human approval."""
    if not thread_id:
        thread_id = f"user_{uuid.uuid4().hex}"

    config = {"configurable": {"thread_id": thread_id}}
    initial_state = {
        "messages": [HumanMessage(content=user_input)],
        "user_query": user_input,
        "guardrail_allowed": True,
        "guardrail_reason": "",
        "selected_agents": [],
        "trip_constraints": _empty_constraints(),
        "supervisor_reasoning": "",
        "flight_results": "",
        "hotel_results": "",
        "weather_results": "",
        "budget_results": "",
        "itinerary": "",
        "approval_request": "",
        "approved": False,
        "human_feedback": "",
        "final_response": "",
        "llm_calls": 0,
    }

    # Execute with automatic reconnect retry on transient network drops
    for attempt in range(2):
        try:
            result = travel_graph.invoke(initial_state, config=config)
            return _serialize_result(result, thread_id)
        except Exception as exc:
            err_msg = str(exc).lower()
            if attempt == 0 and ("connection" in err_msg or "closed" in err_msg or "terminat" in err_msg):
                print(f"[PostgreSQL Auto-Reconnect] Transient connection drop detected: {exc}. Retrying...", flush=True)
                import time
                time.sleep(1)
                continue
            raise


def resume_travel_agent(thread_id: str, approved: bool, feedback: str = "") -> dict[str, Any]:
    """Resume a paused thread with human approval or revision feedback."""
    if not thread_id:
        raise ValueError("thread_id is required to resume a travel plan.")

    config = {"configurable": {"thread_id": thread_id}}
    command = Command(resume={"approved": approved, "feedback": feedback.strip()})

    for attempt in range(2):
        try:
            result = travel_graph.invoke(command, config=config)
            return _serialize_result(result, thread_id)
        except Exception as exc:
            err_msg = str(exc).lower()
            if attempt == 0 and ("connection" in err_msg or "closed" in err_msg or "terminat" in err_msg):
                print(f"[PostgreSQL Auto-Reconnect] Transient connection drop detected on resume: {exc}. Retrying...", flush=True)
                import time
                time.sleep(1)
                continue
            raise
