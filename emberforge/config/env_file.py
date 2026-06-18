"""Read/write key/value pairs in the project .env file."""

from __future__ import annotations

import re
from pathlib import Path

_ENV_LINE = re.compile(r"^([A-Za-z_][A-Za-z0-9_]*)=(.*)$")


def format_env_value(value: str) -> str:
    """Quote values so shell ``source .env`` and pydantic-settings both work."""
    if value == "":
        return '""'
    needs_quotes = any(ch in value for ch in " #,\"'\t$`!*?[]&|;<>()")
    if not needs_quotes:
        return value
    escaped = value.replace("\\", "\\\\").replace('"', '\\"')
    return f'"{escaped}"'


def read_env_values(path: Path) -> dict[str, str]:
    """Parse key/value pairs from a `.env` file."""
    values: dict[str, str] = {}
    if not path.exists():
        return values
    for line in path.read_text(encoding="utf-8").splitlines():
        stripped = line.strip()
        if not stripped or stripped.startswith("#") or "=" not in stripped:
            continue
        key, _, raw = stripped.partition("=")
        key = key.strip()
        value = raw.strip()
        if value.startswith('"') and value.endswith('"'):
            value = value[1:-1].replace('\\"', '"').replace("\\\\", "\\")
        values[key] = value
    return values


def update_env_file(path: Path, updates: dict[str, str]) -> None:
    """Upsert environment variables, preserving comments and unrelated keys."""
    lines: list[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    remaining = dict(updates)
    output: list[str] = []
    seen: set[str] = set()

    for line in lines:
        match = _ENV_LINE.match(line.strip())
        if match:
            key = match.group(1)
            if key in remaining:
                output.append(f"{key}={format_env_value(remaining.pop(key))}")
                seen.add(key)
                continue
        output.append(line)

    for key, value in remaining.items():
        if key not in seen:
            if output and output[-1].strip():
                output.append("")
            output.append(f"{key}={format_env_value(value)}")

    path.write_text("\n".join(output).rstrip() + "\n", encoding="utf-8")