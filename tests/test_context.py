"""Live context providers and location setup tests."""

from __future__ import annotations

from pathlib import Path
from unittest.mock import patch

import httpx
import pytest

from emberforge.config.env_file import update_env_file
from emberforge.services.context import (
    ContextSection,
    ContextService,
    OpenMeteoWeatherProvider,
    RssHeadlinesProvider,
    StaticProfileProvider,
)
from emberforge.services.context_setup import geocode_location
from emberforge.services.conversation import generate_reply
from emberforge.services.personas import get_persona
from emberforge.settings import Settings


def test_format_env_value_quotes_commas_and_spaces():
    from emberforge.config.env_file import format_env_value

    assert format_env_value("Hodgen, Oklahoma, United States") == '"Hodgen, Oklahoma, United States"'
    assert format_env_value("simple") == "simple"


def test_update_env_file_upserts_keys(tmp_path):
    env_path = tmp_path / ".env"
    env_path.write_text("XAI_API_KEY=old\n# comment\n", encoding="utf-8")

    update_env_file(env_path, {"EMBER_LAT": "35.6417", "XAI_API_KEY": "new"})

    text = env_path.read_text(encoding="utf-8")
    assert "XAI_API_KEY=new" in text
    assert 'EMBER_LAT="35.6417"' in text or "EMBER_LAT=35.6417" in text
    assert "# comment" in text


def test_geocode_location_city_comma_state_falls_back_to_city():
    hodgen_payload = {
        "results": [
            {
                "name": "Hodgen",
                "latitude": 34.84177,
                "longitude": -94.63134,
                "timezone": "America/Chicago",
                "country": "United States",
                "admin1": "Oklahoma",
            },
            {
                "name": "Hodgenville",
                "latitude": 37.57395,
                "longitude": -85.73996,
                "timezone": "America/New_York",
                "country": "United States",
                "admin1": "Kentucky",
            },
        ]
    }
    empty_payload: dict = {"results": []}
    calls: list[str] = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(str(request.url))
        if "name=Hodgen%2C" in str(request.url) or "name=Hodgen," in str(request.url):
            return httpx.Response(200, json=empty_payload)
        return httpx.Response(200, json=hodgen_payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.context_setup.httpx.get", side_effect=client.get):
            results = geocode_location("Hodgen, Oklahoma")

    assert len(results) == 1
    assert results[0].name == "Hodgen"
    assert results[0].admin1 == "Oklahoma"
    assert any("name=Hodgen" in call for call in calls)


def test_geocode_location_parses_results():
    payload = {
        "results": [
            {
                "name": "Piedmont",
                "latitude": 35.6417,
                "longitude": -97.7464,
                "timezone": "America/Chicago",
                "country": "United States",
                "admin1": "Oklahoma",
            }
        ]
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.context_setup.httpx.get", side_effect=client.get):
            results = geocode_location("Piedmont Oklahoma")

    assert len(results) == 1
    assert results[0].name == "Piedmont"
    assert results[0].timezone == "America/Chicago"


def test_static_profile_provider_reads_markdown(tmp_path, monkeypatch):
    profile = tmp_path / "prompts" / "user_context.md"
    profile.parent.mkdir(parents=True)
    profile.write_text("- Likes songwriting\n", encoding="utf-8")

    monkeypatch.setenv("EMBERFORGE_ROOT", str(tmp_path))
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_LOCATION_NAME", "Piedmont, Oklahoma")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    settings = Settings(_env_file=None)
    section = StaticProfileProvider(settings).fetch()
    assert section is not None
    assert "songwriting" in section.body
    assert "Piedmont" in section.body


def test_open_meteo_weather_provider_formats_summary(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_LAT", "35.6417")
    monkeypatch.setenv("EMBER_LON", "-97.7464")
    monkeypatch.setenv("EMBER_LOCATION_NAME", "Piedmont, OK")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    settings = Settings()

    payload = {
        "current": {
            "temperature_2m": 72.5,
            "relative_humidity_2m": 55,
            "weather_code": 2,
            "wind_speed_10m": 8.0,
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=payload)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.weather.httpx.get", side_effect=client.get):
            section = OpenMeteoWeatherProvider(settings).fetch()

    assert section is not None
    assert "72°F" in section.body
    assert "partly cloudy" in section.body


def test_rss_headlines_provider_parses_feed(monkeypatch):
    monkeypatch.setenv("XAI_API_KEY", "test-key")
    monkeypatch.setenv("EMBER_RSS_FEEDS", "https://example.test/feed.xml")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    settings = Settings()

    feed_xml = """<?xml version="1.0"?>
    <rss><channel>
      <item><title>First headline</title></item>
      <item><title>Second headline</title></item>
    </channel></rss>"""

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text=feed_xml)

    transport = httpx.MockTransport(handler)
    with httpx.Client(transport=transport) as client:
        with patch("emberforge.services.news_search.httpx.get", side_effect=client.get):
            section = RssHeadlinesProvider(settings).fetch()

    assert section is not None
    assert "First headline" in section.body


@pytest.mark.asyncio
async def test_context_service_fetches_once_per_session(test_settings: Settings, monkeypatch):
    calls = {"count": 0}

    class CountingProvider:
        def fetch(self) -> ContextSection:
            calls["count"] += 1
            return ContextSection(title="Test", body="snapshot body")

    monkeypatch.setenv("EMBER_CONTEXT_ENABLED", "true")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    test_settings = Settings(
        _env_file=None,
        xai_api_key="test-key",
        emberforge_root=str(test_settings.project_root),
    )
    service = ContextService(test_settings, providers=[CountingProvider()])

    first = await service.get_session_context("sess-a")
    second = await service.get_session_context("sess-a")
    third = await service.get_session_context("sess-b")

    assert "snapshot body" in first
    assert first == second
    assert calls["count"] == 2
    assert "snapshot body" in third


@pytest.mark.asyncio
async def test_generate_reply_injects_session_context(test_settings: Settings, monkeypatch):
    monkeypatch.setenv("EMBER_CONTEXT_ENABLED", "true")
    from emberforge.settings import get_settings

    get_settings.cache_clear()
    enabled_settings = Settings(
        _env_file=None,
        xai_api_key="test-key",
        emberforge_root=str(test_settings.project_root),
    )
    ember = get_persona("ember", settings=enabled_settings)

    class FixedProvider:
        def fetch(self) -> ContextSection:
            return ContextSection(title="Weather", body="Piedmont: 70°F, clear")

    context = ContextService(enabled_settings, providers=[FixedProvider()])

    captured: list[dict] = []

    async def fake_post(client, url, **kwargs):
        captured.append(kwargs["json"])
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "Nice day."}}]},
            request=httpx.Request("POST", url),
        )

    with patch("emberforge.services.conversation.post_with_retry", side_effect=fake_post):
        await generate_reply(
            ember,
            "Should I ride today?",
            settings=enabled_settings,
            session_id="ctx-session",
            context_service=context,
        )

    system_content = captured[0]["messages"][0]["content"]
    assert "Local context" in system_content
    assert "70°F" in system_content