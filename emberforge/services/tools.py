"""LLM tool definitions and execution (weather, news)."""

from __future__ import annotations

import json
from typing import Any

from emberforge.services.news_search import fetch_recent_headlines, format_news_results, search_news
from emberforge.services.weather import (
    fetch_current_weather,
    fetch_forecast_weather,
    resolve_weather_place,
)
from emberforge.settings import Settings

_TOOL_INSTRUCTION = """
## Tools (on-demand facts)
You have tools for live weather and news headlines. Call a tool when the user asks for factual weather or news — do not guess.
- Use `get_weather` for today, tomorrow, or multi-day forecasts (any city or home if omitted).
- Use `get_headlines` for general "news today" / top headlines.
- Use `search_news` for headlines about a specific topic or keyword.
After tool results arrive, answer naturally in persona voice using only the returned facts.
"""

TOOL_DEFINITIONS: list[dict[str, Any]] = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": (
                "Get current weather or a daily forecast. "
                "Use when the user asks about weather, temperature, rain, or riding/outdoor conditions."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "location": {
                        "type": "string",
                        "description": "City or region (e.g. Tulsa, Oklahoma). Omit for the user's home location.",
                    },
                    "forecast_days": {
                        "type": "integer",
                        "description": "0 = current conditions only; 1–7 = daily forecast including tomorrow.",
                        "minimum": 0,
                        "maximum": 7,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "get_headlines",
            "description": (
                "Get the latest top headlines from configured RSS feeds. "
                "Use for 'news today', 'what's in the news', or general current events."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "limit": {
                        "type": "integer",
                        "description": "Maximum headlines to return (default from settings).",
                        "minimum": 1,
                        "maximum": 10,
                    },
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_news",
            "description": (
                "Search recent headlines from configured RSS feeds for a topic or keyword. "
                "Use when the user asks about news on a specific subject (e.g. AI, politics)."
            ),
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Topic or keywords to search for in headlines.",
                    },
                },
                "required": ["query"],
            },
        },
    },
]


class ToolService:
    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    @property
    def enabled(self) -> bool:
        return self._settings.tools_enabled

    @property
    def definitions(self) -> list[dict[str, Any]]:
        return TOOL_DEFINITIONS if self.enabled else []

    @property
    def system_instruction(self) -> str:
        return _TOOL_INSTRUCTION if self.enabled else ""

    def execute(self, name: str, arguments_json: str) -> str:
        try:
            args = json.loads(arguments_json) if arguments_json else {}
        except json.JSONDecodeError:
            return "Error: tool arguments were not valid JSON."

        if not isinstance(args, dict):
            return "Error: tool arguments must be a JSON object."

        if name == "get_weather":
            return self._get_weather(args)
        if name == "get_headlines":
            return self._get_headlines(args)
        if name == "search_news":
            return self._search_news(args)
        return f"Error: unknown tool '{name}'."

    def _get_weather(self, args: dict[str, Any]) -> str:
        location = args.get("location")
        if location is not None and not isinstance(location, str):
            return "Error: location must be a string."

        forecast_days = args.get("forecast_days", 0)
        try:
            forecast_days = int(forecast_days)
        except (TypeError, ValueError):
            forecast_days = 0
        forecast_days = max(0, min(forecast_days, 7))

        place = resolve_weather_place(self._settings, location=location)
        if place is None:
            if location:
                return f"Could not find coordinates for '{location}'."
            return (
                "Home location is not configured. Set EMBER_LAT/EMBER_LON in .env "
                "or pass a location name."
            )

        if forecast_days > 0:
            body = fetch_forecast_weather(place, self._settings, days=forecast_days)
        else:
            body = fetch_current_weather(place, self._settings)

        return body or "Weather data is temporarily unavailable."

    def _get_headlines(self, args: dict[str, Any]) -> str:
        if not self._settings.rss_feed_urls:
            return (
                "No RSS feeds configured. Add EMBER_RSS_FEEDS to .env "
                "(comma-separated URLs, e.g. https://feeds.npr.org/1001/rss.xml)."
            )

        limit = args.get("limit")
        if limit is not None:
            try:
                limit = max(1, min(int(limit), 10))
            except (TypeError, ValueError):
                limit = None

        items = fetch_recent_headlines(self._settings, limit=limit)
        return format_news_results(items)

    def _search_news(self, args: dict[str, Any]) -> str:
        query = args.get("query", "")
        if not isinstance(query, str) or not query.strip():
            return "Error: query is required."

        if not self._settings.rss_feed_urls:
            return (
                "No RSS feeds configured. Add EMBER_RSS_FEEDS to .env "
                "(comma-separated URLs, e.g. https://feeds.npr.org/1001/rss.xml)."
            )

        items = search_news(query.strip(), self._settings)
        return format_news_results(items)