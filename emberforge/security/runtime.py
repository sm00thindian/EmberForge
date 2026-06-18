"""Application-wide security singletons."""

from __future__ import annotations

from pathlib import Path

from emberforge.hub.storage.factory import clear_process_security_store, get_process_security_store


def get_security_state() -> dict:
    return get_process_security_store().as_dict()


def reset_security_state() -> None:
    clear_process_security_store()


def security_state_dir_for(root: Path) -> Path:
    return root / ".emberforge"