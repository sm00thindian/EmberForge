"""Interactive location setup for live context (geocoding → .env)."""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import quote

import httpx

from emberforge.config.env_file import update_env_file
from emberforge.settings import Settings, get_settings

_GEOCODE_URL = "https://geocoding-api.open-meteo.com/v1/search"
_US_STATE_NAMES = {
    "alabama",
    "alaska",
    "arizona",
    "arkansas",
    "california",
    "colorado",
    "connecticut",
    "delaware",
    "florida",
    "georgia",
    "hawaii",
    "idaho",
    "illinois",
    "indiana",
    "iowa",
    "kansas",
    "kentucky",
    "louisiana",
    "maine",
    "maryland",
    "massachusetts",
    "michigan",
    "minnesota",
    "mississippi",
    "missouri",
    "montana",
    "nebraska",
    "nevada",
    "new hampshire",
    "new jersey",
    "new mexico",
    "new york",
    "north carolina",
    "north dakota",
    "ohio",
    "oklahoma",
    "oregon",
    "pennsylvania",
    "rhode island",
    "south carolina",
    "south dakota",
    "tennessee",
    "texas",
    "utah",
    "vermont",
    "virginia",
    "washington",
    "west virginia",
    "wisconsin",
    "wyoming",
}


@dataclass(frozen=True)
class GeocodeResult:
    name: str
    latitude: float
    longitude: float
    timezone: str
    country: str
    admin1: str


def _parse_results(payload: dict) -> list[GeocodeResult]:
    results: list[GeocodeResult] = []
    for item in payload.get("results", []):
        name = item.get("name", "")
        if not name:
            continue
        results.append(
            GeocodeResult(
                name=name,
                latitude=float(item["latitude"]),
                longitude=float(item["longitude"]),
                timezone=item.get("timezone", "") or "",
                country=item.get("country", "") or "",
                admin1=item.get("admin1", "") or "",
            )
        )
    return results


def _query_variants(query: str) -> list[str]:
    """Build search variants — Open-Meteo often fails on 'City, State' but finds the city alone."""
    cleaned = re.sub(r"\s+", " ", query.strip())
    if not cleaned:
        return []

    variants: list[str] = []
    seen: set[str] = set()

    def add(value: str) -> None:
        key = value.casefold()
        if value and key not in seen:
            seen.add(key)
            variants.append(value)

    add(cleaned)

    if "," in cleaned:
        city, region = (part.strip() for part in cleaned.split(",", 1))
        add(city)
        if city and region:
            add(f"{city} {region}")

    # "Hodgen OK" → try expanded state name when region looks like a US state
    tokens = cleaned.replace(",", " ").split()
    if len(tokens) >= 2:
        add(tokens[0])

    return variants


def _region_hint(query: str) -> str | None:
    """Return a US state/region hint from the user's query, if any."""
    if "," in query:
        region = query.split(",", 1)[1].strip()
        if region:
            return region

    tokens = query.replace(",", " ").split()
    if len(tokens) >= 2:
        return tokens[-1]
    return None


def _matches_region(result: GeocodeResult, hint: str) -> bool:
    normalized = hint.strip().casefold()
    if not normalized:
        return True
    admin1 = result.admin1.casefold()
    if normalized in admin1 or admin1 in normalized:
        return True
    if normalized in _US_STATE_NAMES and admin1 == normalized:
        return True
    return False


def _rank_results(results: list[GeocodeResult], query: str) -> list[GeocodeResult]:
    hint = _region_hint(query)
    if not hint:
        return results

    preferred = [result for result in results if _matches_region(result, hint)]
    if preferred:
        return preferred

    us_only = [result for result in results if result.country.casefold() == "united states"]
    return us_only or results


def _search_variant(variant: str, *, timeout: float) -> list[GeocodeResult]:
    url = (
        f"{_GEOCODE_URL}?name={quote(variant)}"
        f"&count=10&language=en&format=json&countryCode=US"
    )
    response = httpx.get(url, timeout=timeout)
    response.raise_for_status()
    return _parse_results(response.json())


def geocode_location(query: str, *, timeout: float = 10.0) -> list[GeocodeResult]:
    """Resolve a place name to coordinates via Open-Meteo (no API key)."""
    cleaned = query.strip()
    if not cleaned:
        return []

    merged: list[GeocodeResult] = []
    seen_coords: set[tuple[float, float]] = set()

    for variant in _query_variants(cleaned):
        try:
            batch = _search_variant(variant, timeout=timeout)
        except httpx.HTTPError:
            continue
        for result in batch:
            key = (result.latitude, result.longitude)
            if key in seen_coords:
                continue
            seen_coords.add(key)
            merged.append(result)
        if merged:
            break

    if not merged:
        try:
            url = f"{_GEOCODE_URL}?name={quote(cleaned)}&count=10&language=en&format=json"
            response = httpx.get(url, timeout=timeout)
            response.raise_for_status()
            merged = _parse_results(response.json())
        except httpx.HTTPError:
            return []

    return _rank_results(merged, cleaned)[:5]


def _format_place(result: GeocodeResult) -> str:
    parts = [result.name]
    if result.admin1:
        parts.append(result.admin1)
    if result.country:
        parts.append(result.country)
    return ", ".join(parts)


def _choose_match(matches: list[GeocodeResult], query: str) -> GeocodeResult:
    if len(matches) == 1:
        chosen = matches[0]
        print(f"Using: {_format_place(chosen)}")
        return chosen

    print(f"Matches for '{query}':")
    for index, match in enumerate(matches, start=1):
        print(f"  {index}. {_format_place(match)}")
    while True:
        choice = input(f"Choice [1-{len(matches)}] (default 1): ").strip()
        if not choice:
            return matches[0]
        if choice.isdigit() and 1 <= int(choice) <= len(matches):
            return matches[int(choice) - 1]
        print("Enter a number from the list.")


def _prompt_for_location() -> GeocodeResult | None:
    if not sys.stdin.isatty():
        return None

    max_attempts = 3
    for attempt in range(1, max_attempts + 1):
        query = input("Enter your city or region for local weather context: ").strip()
        if not query:
            print("Skipping location setup — weather context will be unavailable.")
            return None

        try:
            matches = geocode_location(query)
        except httpx.HTTPError as exc:
            print(f"Could not look up location ({exc}). Try again later or set EMBER_LAT/EMBER_LON in .env")
            return None

        if matches:
            return _choose_match(matches, query)

        if attempt < max_attempts:
            print(
                f"No matches for '{query}'. "
                "Try just the city name (e.g. Hodgen) or check spelling."
            )
        else:
            print(
                f"No matches for '{query}'. "
                "Set EMBER_LAT and EMBER_LON manually in .env, or run emberforge serve again."
            )
    return None


def ensure_context_location(
    settings: Settings,
    *,
    env_path: Path | None = None,
    interactive: bool = True,
) -> Settings:
    """
    When context is enabled but coordinates are missing, prompt once and save to .env.
    """
    if not settings.context_enabled or settings.context_location_configured:
        return settings

    if not interactive:
        print(
            "WARNING: EMBER_CONTEXT_ENABLED=true but EMBER_LAT/EMBER_LON are not set. "
            "Weather context disabled until configured."
        )
        return settings

    chosen = _prompt_for_location()
    if chosen is None:
        return settings

    resolved_env = env_path or (settings.project_root / ".env")
    location_name = _format_place(chosen)
    update_env_file(
        resolved_env,
        {
            "EMBER_LAT": f"{chosen.latitude:.4f}",
            "EMBER_LON": f"{chosen.longitude:.4f}",
            "EMBER_LOCATION_NAME": location_name,
            **({"EMBER_TIMEZONE": chosen.timezone} if chosen.timezone else {}),
        },
    )
    print(f"Saved location to {resolved_env}")

    get_settings.cache_clear()
    return Settings()