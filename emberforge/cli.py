"""EmberForge command-line interface."""

from __future__ import annotations

import argparse
import json
import sys
import urllib.error
import urllib.request

import pyotp
import uvicorn

from emberforge import __version__
from emberforge.observability.logging import configure_logging
from emberforge.security.totp import provisioning_uri
from emberforge.services.context_setup import ensure_context_location
from emberforge.settings import Settings, get_settings


def cmd_serve(args: argparse.Namespace) -> int:
    settings = get_settings()
    settings = ensure_context_location(
        settings,
        interactive=not args.non_interactive,
    )
    settings.validate_runtime()
    configure_logging(settings)

    host = args.host or settings.host
    port = args.port or settings.port
    reload = args.reload

    print(f"Starting EmberForge {__version__} on http://{host}:{port}")
    print(f"Setup UI: http://{host}:{port}/setup")
    uvicorn.run(
        "emberforge.api.app:app",
        host=host,
        port=port,
        reload=reload,
        log_level=settings.log_level.lower(),
    )
    return 0


def cmd_check(args: argparse.Namespace) -> int:
    settings = Settings()
    print(f"EmberForge {__version__} configuration check")
    print(f"  project_root:   {settings.project_root}")
    print(f"  personas_dir:   {settings.personas_dir}")
    print(f"  ember_env:      {settings.ember_env}")
    print(f"  xai_api_key:    {'set' if settings.resolved_api_key else 'MISSING'}")
    print(f"  llm_provider:   {settings.llm_provider}")
    print(f"  llm_model:      {settings.llm_model}")
    print(f"  llm_api_url:    {settings.llm_api_url}")
    print(f"  log_json:       {'on' if settings.log_json else 'off'}")
    print(f"  whisper_model:  {settings.whisper_model}")
    print(f"  device_auth:    {'required' if settings.device_auth_required else 'open'}")
    print(f"  admin_auth:     {'configured' if settings.admin_auth_configured else 'none'}")
    print(f"  rate_limits:    {'on' if settings.rate_limits_active else 'off'}")
    print(f"  context:        {'on' if settings.context_enabled else 'off'}")
    if settings.context_enabled:
        if settings.context_location_configured:
            label = settings.location_name or "coordinates set"
            print(f"  location:       {label} ({settings.ember_lat}, {settings.ember_lon})")
        else:
            print("  location:       not configured (set EMBER_LAT/EMBER_LON or run emberforge serve)")
        feeds = settings.rss_feed_urls
        print(f"  rss_feeds:      {len(feeds)} configured" if feeds else "  rss_feeds:      none")
    print(f"  tools:          {'on' if settings.tools_enabled else 'off'}")
    if settings.tools_enabled and not settings.rss_feed_urls:
        print("  WARNING:       EMBER_RSS_FEEDS not set — news tools will not work")

    if settings.is_production:
        from emberforge.security.runtime import get_security_state

        paired = len(get_security_state()["device_registry"].list_devices())
        print(f"  paired_devices: {paired}")

    try:
        settings.validate_runtime()
        from emberforge.services.personas import load_personas

        personas = load_personas(settings)
        print(f"  personas:       {', '.join(sorted(personas))}")
        print("OK — ready to serve")
        return 0
    except Exception as exc:
        print(f"ERROR — {exc}")
        return 1


def _backend_base_url(settings: Settings, override: str | None) -> str:
    if override:
        return override.rstrip("/")
    return f"http://{settings.host}:{settings.port}"


def cmd_pair(args: argparse.Namespace) -> int:
    settings = Settings()
    base = _backend_base_url(settings, args.base_url)
    url = f"{base}/admin/v1/pair/code"

    request = urllib.request.Request(url, method="POST", data=b"")
    try:
        with urllib.request.urlopen(request, timeout=args.timeout) as response:
            payload = json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8", errors="replace")
        print(f"ERROR — pairing request failed ({exc.code}): {body}")
        return 1
    except urllib.error.URLError as exc:
        print(f"ERROR — cannot reach backend at {base}: {exc.reason}")
        print("Start the server with: emberforge serve")
        return 1

    print(f"Pairing code: {payload['code']}")
    print(f"Expires in:   {payload['expires_in']}s")
    print(payload.get("message", "Enter this code on the device."))
    return 0


def cmd_totp_setup(args: argparse.Namespace) -> int:
    settings = Settings()

    if args.generate:
        secret = pyotp.random_base32()
        print("Generated TOTP secret (add to .env):")
        print(f"  EMBER_ADMIN_TOTP_SECRET={secret}")
        print()
        print("Provisioning URI (scan in Google Authenticator, 1Password, or Apple Passwords):")
        print(f"  {provisioning_uri(secret)}")
        return 0

    if not settings.admin_totp_secret:
        print("ERROR — EMBER_ADMIN_TOTP_SECRET is not set. Use --generate to create one.")
        return 1

    print(provisioning_uri(settings.admin_totp_secret))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="emberforge",
        description="EmberForge voice companion backend",
    )
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")

    subparsers = parser.add_subparsers(dest="command", required=True)

    serve = subparsers.add_parser("serve", help="Start the HTTP backend")
    serve.add_argument("--host", default=None, help="Bind host (default from settings)")
    serve.add_argument("--port", type=int, default=None, help="Bind port (default from settings)")
    serve.add_argument("--reload", action="store_true", help="Enable auto-reload (development)")
    serve.add_argument(
        "--non-interactive",
        action="store_true",
        help="Do not prompt for missing location when EMBER_CONTEXT_ENABLED=true",
    )
    serve.set_defaults(func=cmd_serve)

    check = subparsers.add_parser("check", help="Validate configuration and personas")
    check.set_defaults(func=cmd_check)

    pair = subparsers.add_parser("pair", help="Issue a device pairing code (localhost backend)")
    pair.add_argument(
        "--base-url",
        default=None,
        help="Backend URL (default http://EMBER_HOST:EMBER_BACKEND_PORT)",
    )
    pair.add_argument("--timeout", type=float, default=10.0, help="HTTP timeout seconds")
    pair.set_defaults(func=cmd_pair)

    totp = subparsers.add_parser("totp-setup", help="Show or generate admin TOTP provisioning URI")
    totp.add_argument(
        "--generate",
        action="store_true",
        help="Generate a new random secret and provisioning URI",
    )
    totp.set_defaults(func=cmd_totp_setup)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())