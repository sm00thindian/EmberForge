"""On-demand LLM tool tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from emberforge.services.conversation import generate_reply
from emberforge.services.personas import get_persona
from emberforge.services.tool_loop import complete_with_tools
from emberforge.services.tools import ToolService
from emberforge.settings import Settings


def _enabled_settings(test_settings: Settings, monkeypatch) -> Settings:
    monkeypatch.setenv("EMBER_TOOLS_ENABLED", "true")
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_LAT", "34.8418")
    monkeypatch.setenv("EMBER_LON", "-94.6313")
    monkeypatch.setenv("EMBER_LOCATION_NAME", "Hodgen, Oklahoma")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    return Settings(
        _env_file=None,
        emberforge_root=str(test_settings.project_root),
    )


def test_tool_service_get_weather_home(test_settings: Settings, monkeypatch):
    settings = _enabled_settings(test_settings, monkeypatch)
    service = ToolService(settings)

    forecast_payload = {
        "current": {
            "temperature_2m": 70.0,
            "relative_humidity_2m": 50,
            "weather_code": 2,
            "wind_speed_10m": 6.0,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=forecast_payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.weather.httpx.get", side_effect=client.get):
            result = service.execute("get_weather", "{}")

    assert "70°F" in result
    assert "Hodgen" in result


def test_tool_service_get_weather_forecast_days(test_settings: Settings, monkeypatch):
    settings = _enabled_settings(test_settings, monkeypatch)
    service = ToolService(settings)

    forecast_payload = {
        "daily": {
            "time": ["2026-06-17"],
            "temperature_2m_max": [80.0],
            "temperature_2m_min": [60.0],
            "weather_code": [3],
            "precipitation_probability_max": [20],
        }
    }

    geocode_payload = {
        "results": [
            {
                "name": "Tulsa",
                "latitude": 36.15398,
                "longitude": -95.99277,
                "timezone": "America/Chicago",
                "country": "United States",
                "admin1": "Oklahoma",
            }
        ]
    }
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "geocoding-api" in str(request.url):
            return httpx.Response(200, json=geocode_payload)
        return httpx.Response(200, json=forecast_payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.context_setup.httpx.get", side_effect=client.get):
            with patch("emberforge.services.weather.httpx.get", side_effect=client.get):
                result = service.execute(
                    "get_weather",
                    '{"location": "Tulsa, Oklahoma", "forecast_days": 1}',
                )

    assert "forecast" in result.lower()
    assert "Tulsa" in result


def test_is_generic_news_query():
    from emberforge.services.news_search import is_generic_news_query

    assert is_generic_news_query("What is the news today?")
    assert is_generic_news_query("news")
    assert not is_generic_news_query("electric vehicles policy")


def test_tool_service_get_headlines(test_settings: Settings, monkeypatch):
    monkeypatch.setenv("EMBER_RSS_FEEDS", "https://example.test/feed.xml")
    settings = _enabled_settings(test_settings, monkeypatch)
    service = ToolService(settings)

    feed_xml = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Lead story</title><description>Breaking</description></item>
    </channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=feed_xml)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.news_search.httpx.get", side_effect=client.get):
            result = service.execute("get_headlines", "{}")

    assert "Lead story" in result


def test_tool_service_search_news(test_settings: Settings, monkeypatch):
    monkeypatch.setenv("EMBER_RSS_FEEDS", "https://example.test/feed.xml")
    settings = _enabled_settings(test_settings, monkeypatch)
    service = ToolService(settings)

    feed_xml = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>AI breakthrough announced</title><description>Major model update</description></item>
      <item><title>Sports roundup</title><description>Local team wins</description></item>
    </channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=feed_xml)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.news_search.httpx.get", side_effect=client.get):
            result = service.execute("search_news", '{"query": "AI"}')

    assert "AI breakthrough" in result
    assert "Sports roundup" not in result


def test_tool_service_search_news_generic_falls_back_to_headlines(test_settings: Settings, monkeypatch):
    monkeypatch.setenv("EMBER_RSS_FEEDS", "https://example.test/feed.xml")
    settings = _enabled_settings(test_settings, monkeypatch)
    service = ToolService(settings)

    feed_xml = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>Daily briefing</title><description>Overview</description></item>
    </channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=feed_xml)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.news_search.httpx.get", side_effect=client.get):
            result = service.execute("search_news", '{"query": "news today"}')

    assert "Daily briefing" in result


@pytest.mark.asyncio
async def test_complete_with_tools_runs_tool_then_returns_reply(test_settings: Settings, monkeypatch):
    settings = _enabled_settings(test_settings, monkeypatch)
    tool_service = ToolService(settings)
    calls = {"count": 0}

    async def fake_post(client, url, **kwargs):
        calls["count"] += 1
        payload = kwargs["json"]
        if calls["count"] == 1:
            return httpx.Response(
                200,
                json={
                    "choices": [
                        {
                            "message": {
                                "role": "assistant",
                                "content": None,
                                "tool_calls": [
                                    {
                                        "id": "call_1",
                                        "type": "function",
                                        "function": {
                                            "name": "get_weather",
                                            "arguments": '{"forecast_days": 0}',
                                        },
                                    }
                                ],
                            }
                        }
                    ]
                },
                request=httpx.Request("POST", url),
            )
        assert payload["messages"][-1]["role"] == "tool"
        return httpx.Response(
            200,
            json={"choices": [{"message": {"role": "assistant", "content": "It's mild at home."}}]},
            request=httpx.Request("POST", url),
        )

    forecast_payload = {
        "current": {
            "temperature_2m": 68.0,
            "relative_humidity_2m": 40,
            "weather_code": 1,
            "wind_speed_10m": 4.0,
        }
    }

    def weather_handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=forecast_payload)

    transport = httpx.MockTransport(weather_handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.tool_loop.post_with_retry", AsyncMock(side_effect=fake_post)):
            with patch("emberforge.services.weather.httpx.get", side_effect=client.get):
                reply = await complete_with_tools(
                    settings=settings,
                    messages=[{"role": "user", "content": "What's the weather?"}],
                    model="grok-3-latest",
                    temperature=0.5,
                    tool_service=tool_service,
                    request_id="req-tools",
                )

    assert reply == "It's mild at home."
    assert calls["count"] == 2


@pytest.mark.asyncio
async def test_generate_reply_uses_tool_loop_when_enabled(test_settings: Settings, monkeypatch):
    settings = _enabled_settings(test_settings, monkeypatch)
    ember = get_persona("ember", settings=settings)

    with patch(
        "emberforge.services.conversation.complete_with_tools",
        AsyncMock(return_value="Tomorrow looks rainy in Tulsa."),
    ) as tool_loop:
        result = await generate_reply(
            ember,
            "Weather in Tulsa tomorrow?",
            settings=settings,
            tool_service=ToolService(settings),
        )

    tool_loop.assert_awaited_once()
    assert "Tulsa" in result.response_text