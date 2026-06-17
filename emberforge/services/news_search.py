"""Search configured RSS feeds for topic keywords."""

from __future__ import annotations

import xml.etree.ElementTree as ET
from dataclasses import dataclass

import httpx

from emberforge.settings import Settings


@dataclass(frozen=True)
class NewsItem:
    title: str
    summary: str
    source: str


def _parse_feed_items(xml_text: str, *, source: str, limit: int) -> list[NewsItem]:
    items: list[NewsItem] = []
    try:
        root = ET.fromstring(xml_text)
    except ET.ParseError:
        return items

    for node in root.findall(".//item"):
        title = (node.findtext("title") or "").strip()
        summary = (node.findtext("description") or "").strip()
        if title:
            items.append(NewsItem(title=title, summary=summary, source=source))
        if len(items) >= limit:
            return items

    atom_ns = {"atom": "http://www.w3.org/2005/Atom"}
    for entry in root.findall(".//atom:entry", atom_ns):
        title = (entry.findtext("atom:title", default="", namespaces=atom_ns) or "").strip()
        summary = (entry.findtext("atom:summary", default="", namespaces=atom_ns) or "").strip()
        if title:
            items.append(NewsItem(title=title, summary=summary, source=source))
        if len(items) >= limit:
            break
    return items


_GENERIC_NEWS_PHRASES = frozenset(
    {
        "news",
        "the news",
        "news today",
        "today's news",
        "headlines",
        "top stories",
        "top headlines",
        "current events",
        "what's the news",
        "whats the news",
        "what is the news",
        "what is the news today",
        "any news",
    }
)


def is_generic_news_query(query: str) -> bool:
    """True when the user wants top headlines, not a keyword search."""
    normalized = " ".join(query.strip().casefold().replace("?", "").split())
    if not normalized:
        return True
    if normalized in _GENERIC_NEWS_PHRASES:
        return True
    words = set(normalized.split())
    if "news" in words and len(words) <= 6:
        return True
    return False


def _matches_query(item: NewsItem, query: str) -> bool:
    needle = query.casefold()
    haystacks = (item.title, item.summary, item.source)
    return any(needle in value.casefold() for value in haystacks if value)


def fetch_recent_headlines(settings: Settings, *, limit: int | None = None) -> list[NewsItem]:
    feeds = settings.rss_feed_urls
    if not feeds:
        return []

    max_results = limit or settings.context_max_headlines
    timeout = settings.context_fetch_timeout_seconds
    headlines: list[NewsItem] = []

    for feed_url in feeds:
        if len(headlines) >= max_results:
            break
        try:
            response = httpx.get(feed_url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            headlines.extend(
                _parse_feed_items(response.text, source=feed_url, limit=max_results - len(headlines))
            )
        except httpx.HTTPError:
            continue
    return headlines[:max_results]


def search_news(query: str, settings: Settings, *, limit: int | None = None) -> list[NewsItem]:
    feeds = settings.rss_feed_urls
    if not feeds or not query.strip():
        return []

    if is_generic_news_query(query):
        return fetch_recent_headlines(settings, limit=limit)

    max_results = limit or settings.context_max_headlines
    timeout = settings.context_fetch_timeout_seconds
    matches: list[NewsItem] = []

    for feed_url in feeds:
        if len(matches) >= max_results:
            break
        try:
            response = httpx.get(feed_url, timeout=timeout, follow_redirects=True)
            response.raise_for_status()
            items = _parse_feed_items(response.text, source=feed_url, limit=50)
        except httpx.HTTPError:
            continue

        for item in items:
            if _matches_query(item, query):
                matches.append(item)
            if len(matches) >= max_results:
                break

    return matches[:max_results]


def format_news_results(items: list[NewsItem]) -> str:
    if not items:
        return "No matching headlines found in configured RSS feeds."
    lines = []
    for item in items:
        line = f"- {item.title}"
        if item.summary:
            snippet = " ".join(item.summary.split())
            if len(snippet) > 160:
                snippet = snippet[:157] + "..."
            line += f" — {snippet}"
        lines.append(line)
    return "\n".join(lines)