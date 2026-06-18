"""Local network helpers for hub URLs."""

from __future__ import annotations

import socket


def primary_lan_ipv4() -> str | None:
    """Best-effort primary LAN IPv4 for this machine."""
    try:
        with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as sock:
            sock.connect(("8.8.8.8", 80))
            return sock.getsockname()[0]
    except OSError:
        return None


def local_client_host(bind_host: str) -> str:
    """Host clients on the same machine should use to reach the backend."""
    if bind_host in {"0.0.0.0", "::"}:
        return "127.0.0.1"
    return bind_host


def format_serve_urls(bind_host: str, port: int) -> list[str]:
    """Human-readable setup URLs for console output."""
    local = f"http://127.0.0.1:{port}/setup"
    lines = [f"Setup UI (local): {local}"]

    if bind_host in {"0.0.0.0", "::"}:
        lan_ip = primary_lan_ipv4()
        if lan_ip:
            lines.append(f"Setup UI (LAN):   http://{lan_ip}:{port}/setup")
        else:
            lines.append(f"Setup UI (LAN):   http://<this-host-ip>:{port}/setup")

    return lines