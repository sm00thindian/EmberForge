"""Open-Meteo weather helpers (current + forecast)."""

from __future__ import annotations

from dataclasses import dataclass

import httpx

from emberforge.services.context_setup import GeocodeResult, geocode_location
from emberforge.settings import Settings

_WMO_WEATHER: dict[int, str] = {
    0: "clear",
    1: "mainly clear",
    2: "partly cloudy",
    3: "overcast",
    45: "fog",
    48: "fog",
    51: "light drizzle",
    53: "drizzle",
    55: "heavy drizzle",
    61: "light rain",
    63: "rain",
    65: "heavy rain",
    71: "light snow",
    73: "snow",
    75: "heavy snow",
    80: "rain showers",
    81: "rain showers",
    82: "heavy rain showers",
    95: "thunderstorm",
}


@dataclass(frozen=True)
class WeatherPlace:
    label: str
    latitude: float
    longitude: float
    timezone: str


def wmo_summary(code: int) -> str:
    return _WMO_WEATHER.get(code, "current conditions")


def resolve_weather_place(
    settings: Settings,
    *,
    location: str | None = None,
) -> WeatherPlace | None:
    if location and location.strip():
        matches = geocode_location(location.strip())
        if not matches:
            return None
        chosen = matches[0]
        return WeatherPlace(
            label=_format_place(chosen),
            latitude=chosen.latitude,
            longitude=chosen.longitude,
            timezone=chosen.timezone or settings.timezone or "auto",
        )

    if settings.context_location_configured:
        return WeatherPlace(
            label=settings.location_name or "home",
            latitude=float(settings.ember_lat),
            longitude=float(settings.ember_lon),
            timezone=settings.timezone or "auto",
        )
    return None


def _format_place(result: GeocodeResult) -> str:
    parts = [result.name]
    if result.admin1:
        parts.append(result.admin1)
    if result.country:
        parts.append(result.country)
    return ", ".join(parts)


def fetch_current_weather(place: WeatherPlace, settings: Settings) -> str | None:
    params = {
        "latitude": place.latitude,
        "longitude": place.longitude,
        "current": "temperature_2m,relative_humidity_2m,weather_code,wind_speed_10m",
        "temperature_unit": "fahrenheit",
        "wind_speed_unit": "mph",
        "timezone": place.timezone,
    }
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=settings.context_fetch_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError:
        return None

    current = payload.get("current", {})
    temp = current.get("temperature_2m")
    humidity = current.get("relative_humidity_2m")
    wind = current.get("wind_speed_10m")
    code = int(current.get("weather_code", -1))
    summary = wmo_summary(code)

    pieces: list[str] = []
    if temp is not None:
        pieces.append(f"{temp:.0f}°F, {summary}")
    else:
        pieces.append(summary)
    if humidity is not None:
        pieces.append(f"humidity {humidity:.0f}%")
    if wind is not None:
        pieces.append(f"wind {wind:.0f} mph")

    return f"{place.label}: {', '.join(pieces)}"


def fetch_forecast_weather(
    place: WeatherPlace,
    settings: Settings,
    *,
    days: int,
) -> str | None:
    forecast_days = max(1, min(days, 7))
    params = {
        "latitude": place.latitude,
        "longitude": place.longitude,
        "daily": "weather_code,temperature_2m_max,temperature_2m_min,precipitation_probability_max",
        "temperature_unit": "fahrenheit",
        "timezone": place.timezone,
        "forecast_days": forecast_days,
    }
    try:
        response = httpx.get(
            "https://api.open-meteo.com/v1/forecast",
            params=params,
            timeout=settings.context_fetch_timeout_seconds,
        )
        response.raise_for_status()
        payload = response.json()
    except httpx.HTTPError:
        return None

    daily = payload.get("daily", {})
    dates = daily.get("time", [])
    highs = daily.get("temperature_2m_max", [])
    lows = daily.get("temperature_2m_min", [])
    codes = daily.get("weather_code", [])
    precip = daily.get("precipitation_probability_max", [])

    if not dates:
        return None

    lines = [f"{place.label} — {forecast_days}-day forecast:"]
    for index, date in enumerate(dates):
        high = highs[index] if index < len(highs) else None
        low = lows[index] if index < len(lows) else None
        code = int(codes[index]) if index < len(codes) else -1
        rain_chance = precip[index] if index < len(precip) else None
        summary = wmo_summary(code)

        parts = [summary]
        if high is not None and low is not None:
            parts.insert(0, f"{low:.0f}–{high:.0f}°F")
        if rain_chance is not None:
            parts.append(f"{rain_chance:.0f}% precip")
        lines.append(f"- {date}: {', '.join(parts)}")

    return "\n".join(lines)