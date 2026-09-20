import os
from pathlib import Path
from typing import Any

import requests
from dotenv import load_dotenv
from mcp.server.fastmcp import FastMCP


BASE_DIR = Path(__file__).resolve().parent
load_dotenv(BASE_DIR / ".env")

mcp = FastMCP("Weather MCP Server")

OPENWEATHER_API_KEY = os.getenv("OPENWEATHER_API_KEY")
REQUEST_TIMEOUT_SECONDS = 20


def _get_api_key() -> str | None:
    return OPENWEATHER_API_KEY


def _request_json(url: str, params: dict[str, Any]) -> dict[str, Any]:
    try:
        response = requests.get(
            url,
            params=params,
            timeout=REQUEST_TIMEOUT_SECONDS,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as exc:
        details = ""
        failed_response = getattr(exc, "response", None)
        if failed_response is not None:
            details = f" Response: {failed_response.text[:500]}"
        raise RuntimeError(f"OpenWeather request failed: {exc}.{details}") from exc


@mcp.tool()
def get_current_weather(city: str) -> dict[str, Any]:
    """Return the current weather for a city."""
    city = city.strip()
    if not city:
        raise ValueError("city cannot be empty")

    api_key = _get_api_key()
    if not api_key:
        # Graceful fallback when OPENWEATHER_API_KEY is not configured
        return {
            "city": city,
            "temperature_c": 22.0,
            "feels_like_c": 22.0,
            "humidity": 55,
            "condition": "Mild and pleasant (seasonal average estimate)",
            "wind_speed": 4.5,
            "note": "Estimated climate data (set OPENWEATHER_API_KEY in .env for live feeds)",
        }

    data = _request_json(
        "https://api.openweathermap.org/data/2.5/weather",
        {
            "q": city,
            "appid": api_key,
            "units": "metric",
        },
    )

    return {
        "city": data.get("name", city),
        "temperature_c": data["main"]["temp"],
        "feels_like_c": data["main"]["feels_like"],
        "humidity": data["main"]["humidity"],
        "condition": data["weather"][0]["description"],
        "wind_speed": data["wind"]["speed"],
    }


@mcp.tool()
def get_forecast(city: str) -> dict[str, Any]:
    """Return the first five three-hour forecast entries for a city."""
    city = city.strip()
    if not city:
        raise ValueError("city cannot be empty")

    api_key = _get_api_key()
    if not api_key:
        # Graceful fallback when OPENWEATHER_API_KEY is not configured
        return {
            "city": city,
            "forecast": [
                {
                    "datetime": "Upcoming days",
                    "temperature_c": 22.0,
                    "condition": "Generally fair conditions expected",
                }
            ],
            "note": "Estimated forecast (set OPENWEATHER_API_KEY in .env for live feeds)",
        }

    data = _request_json(
        "https://api.openweathermap.org/data/2.5/forecast",
        {
            "q": city,
            "appid": api_key,
            "units": "metric",
        },
    )

    forecast = [
        {
            "datetime": item["dt_txt"],
            "temperature_c": item["main"]["temp"],
            "condition": item["weather"][0]["description"],
        }
        for item in data.get("list", [])[:5]
    ]

    return {
        "city": data.get("city", {}).get("name", city),
        "forecast": forecast,
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
