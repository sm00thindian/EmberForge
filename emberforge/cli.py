"""EmberForge command-line interface."""

from __future__ import annotations

import argparse
import sys

import uvicorn

from emberforge import __version__
from emberforge.settings import Settings, get_settings


def cmd_serve(args: argparse.Namespace) -> int:
    settings = get_settings()
    settings.validate_runtime()

    host = args.host or settings.host
    port = args.port or settings.port
    reload = args.reload

    print(f"Starting EmberForge {__version__} on http://{host}:{port}")
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
    print(f"  project_root:  {settings.project_root}")
    print(f"  personas_dir:  {settings.personas_dir}")
    print(f"  xai_api_key:   {'set' if settings.resolved_api_key else 'MISSING'}")
    print(f"  whisper_model: {settings.whisper_model}")
    print(f"  device_auth:   {'required' if settings.device_auth_required else 'open'}")

    try:
        settings.validate_runtime()
        from emberforge.services.personas import load_personas

        personas = load_personas(settings)
        print(f"  personas:      {', '.join(sorted(personas))}")
        print("OK — ready to serve")
        return 0
    except Exception as exc:
        print(f"ERROR — {exc}")
        return 1


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
    serve.set_defaults(func=cmd_serve)

    check = subparsers.add_parser("check", help="Validate configuration and personas")
    check.set_defaults(func=cmd_check)

    return parser


def main(argv: list[str] | None = None) -> int:
    parser = build_parser()
    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    sys.exit(main())