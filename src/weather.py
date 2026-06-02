"""
src/weather.py
--------------
Fetches today's weather forecast for a given location.
Public entry point: get_weather(location: str) -> str
  Returns a formatted string like "Heavy drizzle — 14–18°C, 1.0mm rain"
  or an empty string if the API call fails.
"""
from __future__ import annotations
import requests

# ── Location coordinates ─────────────────────────────────────────────────────
LOCATIONS: dict[str, tuple[float, float]] = {
    "dublin":    (53.3498, -6.2603),
    "waterford": (52.2593, -7.1101),
    "holiday":   (53.3498, -6.2603),  # fallback to Dublin
}
DEFAULT_COORDS = (53.3498, -6.2603)

# ── WMO weather code descriptions ────────────────────────────────────────────
WMO_CODES: dict[int, str] = {
    0:  "Clear sky",
    1:  "Mainly clear",
    2:  "Partly cloudy",
    3:  "Overcast",
    45: "Foggy",
    48: "Icy fog",
    51: "Light drizzle",
    53: "Drizzle",
    55: "Heavy drizzle",
    61: "Light rain",
    63: "Rain",
    65: "Heavy rain",
    71: "Light snow",
    73: "Snow",
    75: "Heavy snow",
    80: "Light showers",
    81: "Showers",
    82: "Heavy showers",
    95: "Thunderstorm",
}

# ── Emoji icons keyed on WMO description ─────────────────────────────────────
WEATHER_ICONS: dict[str, str] = {
    "Clear sky":      "☀️",
    "Mainly clear":   "🌤️",
    "Partly cloudy":  "⛅",
    "Overcast":       "☁️",
    "Foggy":          "🌫️",
    "Icy fog":        "🌫️",
    "Light drizzle":  "🌦️",
    "Drizzle":        "🌧️",
    "Heavy drizzle":  "🌧️",
    "Light rain":     "🌦️",
    "Rain":           "🌧️",
    "Heavy rain":     "🌧️",
    "Light snow":     "🌨️",
    "Snow":           "❄️",
    "Heavy snow":     "❄️",
    "Light showers":  "🌦️",
    "Showers":        "🌧️",
    "Heavy showers":  "⛈️",
    "Thunderstorm":   "⛈️",
    "Mixed conditions": "🌥️",
}


def get_weather(location: str) -> str:
    """Fetch today's weather forecast for the given location.

    Returns a formatted string e.g. "Heavy drizzle — 14–18°C, 1.0mm rain",
    or an empty string if the request fails for any reason.
    """
    lat, lon = LOCATIONS.get(location.lower(), DEFAULT_COORDS)
    try:
        resp = requests.get(
            "https://api.open-meteo.com/v1/forecast",
            params={
                "latitude":     lat,
                "longitude":    lon,
                "daily":        "temperature_2m_max,temperature_2m_min,precipitation_sum,weathercode",
                "timezone":     "Europe/Dublin",
                "forecast_days": 1,
            },
            timeout=5,
        )
        data  = resp.json()
        daily = data["daily"]
        max_temp = round(daily["temperature_2m_max"][0])
        min_temp = round(daily["temperature_2m_min"][0])
        precip   = daily["precipitation_sum"][0]
        code     = daily["weathercode"][0]
        description = WMO_CODES.get(code, "Mixed conditions")
        rain_str    = f", {precip}mm rain" if precip > 0.2 else ""
        return f"{description} — {min_temp}–{max_temp}°C{rain_str}"
    except Exception:
        return ""


def get_weather_icon(weather_str: str) -> str:
    """Return the emoji icon for a weather string returned by get_weather().
    Matches on prefix so 'Heavy drizzle — ...' correctly maps to 🌧️.
    Returns an empty string if no match found.
    """
    for desc, icon in WEATHER_ICONS.items():
        if weather_str.startswith(desc):
            return icon
    return ""