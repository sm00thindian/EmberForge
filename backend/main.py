"""
Compatibility shim — use the emberforge package instead.

    python -m emberforge serve
    emberforge serve

This module re-exports the app for:
    uvicorn backend.main:app
"""

from emberforge.api.app import app, create_app

__all__ = ["app", "create_app"]