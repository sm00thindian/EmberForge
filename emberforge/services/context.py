"""Live context providers (profile, weather, headlines) for LLM sessions."""

from __future__ import annotations

import asyncio
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime, timezone
from threading import Lock
from zoneinfo import ZoneInfo

from emberforge.services.news_search import fetch_recent_headlines
from emberforge.services.weather import fetch_current_weather, resolve_weather_place
from emberforge.settings import Settings


@dataclass(frozen=True)
class ContextSection:
    title: str
    body: str


class ContextProvider(ABC):
    @abstractmethod
    def fetch(self) -> ContextSection | None:
        """Return a context section, or None when unavailable."""


class StaticProfileProvider(ContextProvider):
    """User profile from markdown file and optional env overrides."""

    def __init__(self, settings: Settings) -> None:
        self._settings = settings

    def fetch(self) -> ContextSection | None:
        parts: list[str] = []

        if self._settings.location_name:
            parts.append(f"Location label: {self._settings.location_name}")
        if self._settings.timezone:
            parts.append(f"Timezone: {self._settings.timezone}")

        profile_path = self._settings.project_root / self._settings.context_profile_file
        if profile_path.is_file():
            content = profile_path.read_text(encoding="utf-8").strip()
            if content:
                parts.append(content)

        if not parts:
            return None
        return ContextSection(title="About the user", body="\n".join(parts))


class OpenMeteoWeatherProvider(ContextProvider):
    """Current conditions from Open-Meteo (cached, no API key)."""

    def __init__(
        self,
        settings: Settings,
        *,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        self._settings = settings
        self._cache_ttl = cache_ttl_seconds or settings.context_weather_cache_ttl_seconds
        self._cached_body: str | None = None
        self._cached_at: float = 0.0
        self._lock = Lock()

    def fetch(self) -> ContextSection | None:
        if not self._settings.context_location_configured:
            return None

        with self._lock:
            if self._cached_body and (time.monotonic() - self._cached_at) < self._cache_ttl:
                return ContextSection(title="Weather", body=self._cached_body)

        body = self._fetch_current()
        if not body:
            return None

        with self._lock:
            self._cached_body = body
            self._cached_at = time.monotonic()
        return ContextSection(title="Weather", body=body)

    def _fetch_current(self) -> str | None:
        place = resolve_weather_place(self._settings)
        if place is None:
            return None
        return fetch_current_weather(place, self._settings)


class RssHeadlinesProvider(ContextProvider):
    """Headlines from configurable RSS feeds (cached)."""

    def __init__(
        self,
        settings: Settings,
        *,
        cache_ttl_seconds: float | None = None,
    ) -> None:
        self._settings = settings
        self._cache_ttl = cache_ttl_seconds or settings.context_rss_cache_ttl_seconds
        self._cached_body: str | None = None
        self._cached_at: float = 0.0
        self._lock = Lock()

    def fetch(self) -> ContextSection | None:
        feeds = self._settings.rss_feed_urls
        if not feeds:
            return None

        with self._lock:
            if self._cached_body and (time.monotonic() - self._cached_at) < self._cache_ttl:
                return ContextSection(title="Headlines", body=self._cached_body)

        items = fetch_recent_headlines(self._settings)
        if not items:
            return None

        body = "\n".join(f"- {item.title}" for item in items)
        with self._lock:
            self._cached_body = body
            self._cached_at = time.monotonic()
        return ContextSection(title="Headlines", body=body)


class ContextService:
    """Build a once-per-session context block for the system prompt."""

    def __init__(self, settings: Settings, providers: list[ContextProvider] | None = None) -> None:
        self._settings = settings
        self._providers = providers or [
            StaticProfileProvider(settings),
            OpenMeteoWeatherProvider(settings),
            RssHeadlinesProvider(settings),
        ]
        self._session_snapshots: dict[str, str] = {}
        self._lock = Lock()

    @property
    def enabled(self) -> bool:
        return self._settings.context_enabled

    def clear_session(self, session_id: str) -> None:
        with self._lock:
            self._session_snapshots.pop(session_id, None)

    def reset(self) -> None:
        with self._lock:
            self._session_snapshots.clear()

    async def get_session_context(self, session_id: str) -> str:
        if not self.enabled or not session_id:
            return ""

        with self._lock:
            cached = self._session_snapshots.get(session_id)
            if cached is not None:
                return cached

        snapshot = await asyncio.to_thread(self._build_snapshot)
        with self._lock:
            self._session_snapshots[session_id] = snapshot
        return snapshot

    def _build_snapshot(self) -> str:
        sections: list[ContextSection] = []
        for provider in self._providers:
            try:
                section = provider.fetch()
            except Exception:
                continue
            if section and section.body.strip():
                sections.append(section)

        if not sections:
            return ""

        timestamp = self._format_snapshot_time()
        lines = [
            "## Local context (session snapshot)",
            f"Fetched: {timestamp}",
            "Use when relevant; do not recite verbatim unless asked.",
            "",
        ]
        for section in sections:
            lines.append(f"### {section.title}")
            lines.append(section.body.strip())
            lines.append("")
        return "\n".join(lines).rstrip()

    def _format_snapshot_time(self) -> str:
        tz_name = self._settings.timezone
        now = datetime.now(timezone.utc)
        if tz_name:
            try:
                now = now.astimezone(ZoneInfo(tz_name))
            except Exception:
                pass
        return now.strftime("%Y-%m-%d %H:%M %Z").strip()