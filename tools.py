"""Tools the agent can call.

Each tool has two parts:
  1. A JSON schema (in TOOLS) - this is all Claude ever sees. It reads the
     name + description to decide WHEN to call it, and the input_schema to
     decide WHAT arguments to send.
  2. A plain Python function - this runs on YOUR machine when Claude asks.
     Claude never runs code; it only asks us to.

Data is fake on purpose, so the loop is easy to follow and costs nothing.
"""

from datetime import datetime
from zoneinfo import ZoneInfo

# --- Fake data ------------------------------------------------------------

CITIES = {
    "paris": {
        "timezone": "Europe/Paris",
        "weather": {"temp_c": 14, "condition": "light rain", "humidity": 82},
        "attractions": {
            "indoor": ["Louvre Museum", "Musée d'Orsay", "Galeries Lafayette"],
            "outdoor": ["Eiffel Tower", "Seine river walk", "Montmartre"],
        },
    },
    "berlin": {
        "timezone": "Europe/Berlin",
        "weather": {"temp_c": 9, "condition": "cloudy", "humidity": 70},
        "attractions": {
            "indoor": ["Pergamon Museum", "Reichstag dome", "KaDeWe"],
            "outdoor": ["Brandenburg Gate", "East Side Gallery", "Tiergarten"],
        },
    },
    "tokyo": {
        "timezone": "Asia/Tokyo",
        "weather": {"temp_c": 22, "condition": "sunny", "humidity": 55},
        "attractions": {
            "indoor": ["teamLab Planets", "Tokyo National Museum", "Akihabara arcades"],
            "outdoor": ["Senso-ji Temple", "Shinjuku Gyoen", "Shibuya Crossing"],
        },
    },
}


class ToolError(Exception):
    """Raised when a tool can't do its job. The agent sends it back to
    Claude as an error result, and Claude can try something else."""


def _city(name: str) -> dict:
    key = name.strip().lower()
    if key not in CITIES:
        known = ", ".join(c.title() for c in CITIES)
        raise ToolError(f"Unknown city '{name}'. Known cities: {known}.")
    return CITIES[key]


# --- Tool functions -------------------------------------------------------

def get_weather(city: str) -> dict:
    return {"city": city.title(), **_city(city)["weather"]}


def get_local_time(city: str) -> dict:
    now = datetime.now(ZoneInfo(_city(city)["timezone"]))
    return {"city": city.title(), "local_time": now.strftime("%A %H:%M")}


def find_attractions(city: str, setting: str = "any") -> dict:
    places = _city(city)["attractions"]
    if setting == "any":
        result = places["indoor"] + places["outdoor"]
    else:
        result = places[setting]
    return {"city": city.title(), "setting": setting, "attractions": result}


# Name -> function. The agent looks up the function by the name Claude sends.
TOOL_FUNCTIONS = {
    "get_weather": get_weather,
    "get_local_time": get_local_time,
    "find_attractions": find_attractions,
}

# --- Tool schemas (what Claude sees) --------------------------------------

TOOLS = [
    {
        "name": "get_weather",
        "description": "Get the current weather for a city: temperature in "
                       "Celsius, condition (e.g. rain, sunny) and humidity.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. Paris"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "get_local_time",
        "description": "Get the current local day and time in a city.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name, e.g. Tokyo"},
            },
            "required": ["city"],
            "additionalProperties": False,
        },
        "strict": True,
    },
    {
        "name": "find_attractions",
        "description": "List tourist attractions in a city. Use setting "
                       "'indoor' when the weather is bad, 'outdoor' when it is "
                       "good, or 'any'.",
        "input_schema": {
            "type": "object",
            "properties": {
                "city": {"type": "string", "description": "City name"},
                "setting": {"type": "string", "enum": ["indoor", "outdoor", "any"]},
            },
            "required": ["city", "setting"],
            "additionalProperties": False,
        },
        "strict": True,
    },
]
