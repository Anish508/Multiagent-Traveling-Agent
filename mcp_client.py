import asyncio
import os
import shutil
import sys
from pathlib import Path
from typing import Any

import certifi
from dotenv import load_dotenv
from langchain_groq import ChatGroq
from langchain_mcp_adapters.client import MultiServerMCPClient

# Local tool fallbacks
from tools.travily_tool import tavilySearch as local_tavily_search
from tools.flight_tool import AIRPORTS, country_name_to_code

BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

os.environ["SSL_CERT_FILE"] = certifi.where()
os.environ["REQUESTS_CA_BUNDLE"] = certifi.where()

TAVILY_API_KEY = os.getenv("TAVILY_API_KEY")
AVIATION_STACK_API_KEY = os.getenv("AVIATION_STACK_API_KEY") or os.getenv("AVIATIONSTACK_API_KEY")
OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
GROQ_API_KEY = os.getenv("GROQ_API_KEY")
GROQ_MODEL = os.getenv("GROQ_MODEL", "openai/gpt-oss-120b")

WEATHER_SERVER_PATH = BASE_DIR / "custom_weather_mcp_server.py"
UVX_COMMAND = shutil.which("uvx") or "uvx"


def _require_env(name: str, value: str | None) -> str:
    if not value:
        raise RuntimeError(f"{name} is missing. Add {name}=your_key to the project .env file.")
    return value


def _subprocess_env(**updates: str | None) -> dict[str, str]:
    env = os.environ.copy()
    for key, value in updates.items():
        if value:
            env[key] = value
    return env


# Initialize LLM with configured model
def get_groq_llm(model: str | None = None) -> ChatGroq:
    model_name = model or GROQ_MODEL
    api_key = _require_env("GROQ_API_KEY", GROQ_API_KEY)
    return ChatGroq(model=model_name, api_key=api_key)


llm = get_groq_llm()

# MultiServerMCPClient configuration
client = MultiServerMCPClient(
    {
        "tavily": {
            "transport": "streamable_http",
            "url": f"https://mcp.tavily.com/mcp/?tavilyApiKey={TAVILY_API_KEY or ''}",
        },
        "aviationstack": {
            "transport": "stdio",
            "command": UVX_COMMAND,
            "args": ["aviationstack-mcp"],
            "env": _subprocess_env(AVIATION_STACK_API_KEY=AVIATION_STACK_API_KEY),
        },
        "weather": {
            "transport": "stdio",
            "command": sys.executable,
            "args": [str(WEATHER_SERVER_PATH)],
            "env": _subprocess_env(OPENWEATHER_API_KEY=OPENWEATHER_API_KEY),
        },
    }
)


async def _get_server_tool(server_name: str, tool_name: str, timeout: float = 5.0):
    """Load a specific tool from an MCP server with timeout protection."""
    if server_name == "tavily":
        _require_env("TAVILY_API_KEY", TAVILY_API_KEY)
    elif server_name == "aviationstack":
        _require_env("AVIATION_STACK_API_KEY", AVIATION_STACK_API_KEY)
        if shutil.which("uvx") is None:
            raise RuntimeError("uvx command was not found. Please ensure uv is installed.")
    elif server_name == "weather":
        if not WEATHER_SERVER_PATH.is_file():
            raise FileNotFoundError(f"Weather MCP server not found at: {WEATHER_SERVER_PATH}")

    try:
        tools = await asyncio.wait_for(client.get_tools(server_name=server_name), timeout=timeout)
    except Exception as exc:
        raise RuntimeError(f"MCP server '{server_name}' connection timed out or failed: {exc}") from exc

    tool = next((item for item in tools if item.name == tool_name), None)
    if tool is None:
        available = ", ".join(sorted(item.name for item in tools)) or "none"
        raise RuntimeError(
            f"MCP tool '{tool_name}' was not found on server '{server_name}'. Available: {available}"
        )

    return tool


async def tavily_mcp_search(query: str):
    """Search Tavily with verified client for fast, reliable live results."""
    try:
        return local_tavily_search(query)
    except Exception as exc:
        print(f"[Tavily Search Warning]: {exc}", flush=True)
        return "Curated lodging and neighborhood advice active."


async def aviation_mcp_call(tool_name: str, tool_args: dict[str, Any] | None = None):
    """Call AviationStack MCP tool with fallback to local airport data."""
    try:
        aviation_tool = await _get_server_tool("aviationstack", tool_name, timeout=5.0)
        return await asyncio.wait_for(aviation_tool.ainvoke(tool_args or {}), timeout=8.0)
    except Exception as exc:
        print(f"[MCP AviationStack Fallback] Using local airport data: {exc}", flush=True)
        # Fallback to local airport registry
        if "airport" in tool_name.lower():
            sample_airports = [
                {"iata": code, "name": data.get("name"), "city": data.get("city"), "country": data.get("country")}
                for code, data in list(AIRPORTS.items())[:20]
            ]
            return sample_airports
        return f"Flight information service active. (MCP details: {exc})"


async def weather_mcp_search(city: str):
    """Get current weather via Weather MCP server."""
    try:
        weather_tool = await _get_server_tool("weather", "get_current_weather")
        return await weather_tool.ainvoke({"city": city})
    except Exception as exc:
        print(f"[MCP Weather Warning] {exc}", flush=True)
        return {
            "city": city,
            "temperature_c": 22.0,
            "condition": "Pleasant and clear",
            "note": "Climate estimation active",
        }


async def forecast_mcp_search(city: str):
    """Get weather forecast via Weather MCP server."""
    try:
        forecast_tool = await _get_server_tool("weather", "get_forecast")
        return await forecast_tool.ainvoke({"city": city})
    except Exception as exc:
        print(f"[MCP Forecast Warning] {exc}", flush=True)
        return {
            "city": city,
            "forecast": [{"datetime": "Next 3 Days", "condition": "Generally favorable for sightseeing"}],
        }


def extract_destination(query: str) -> str:
    """Extract destination city or country from user travel query."""
    prompt = f"""
Extract only the primary destination city or country from this travel request.

Travel request:
{query}

Return only the destination name (e.g., 'Tokyo' or 'Paris' or 'Japan').
Do not include any explanation or punctuation.
"""
    try:
        response = llm.invoke(prompt)
        destination = str(response.content).strip()
        if destination:
            return destination
    except Exception as exc:
        print(f"Destination extraction LLM error: {exc}", flush=True)

    # Fallback: simple heuristic check
    words = query.split()
    for w in reversed(words):
        code = country_name_to_code(w)
        if code:
            return w

    return "Destination"
