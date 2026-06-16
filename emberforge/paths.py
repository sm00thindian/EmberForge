"""Resolve project root (personas/, prompts/, voices/)."""

from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path


def _has_project_markers(path: Path) -> bool:
    return (path / "personas").is_dir() and (path / "pyproject.toml").is_file()


@lru_cache
def get_project_root() -> Path:
    """
    Find the EmberForge project root.

    Search order:
    1. EMBERFORGE_ROOT environment variable
    2. Current working directory and parents
    3. Package parent (editable install from repo)
    """
    env_root = os.getenv("EMBERFORGE_ROOT")
    if env_root:
        root = Path(env_root).resolve()
        if _has_project_markers(root):
            return root
        raise FileNotFoundError(f"EMBERFORGE_ROOT is not a valid project root: {root}")

    cwd = Path.cwd().resolve()
    for candidate in [cwd, *cwd.parents]:
        if _has_project_markers(candidate):
            return candidate

    package_parent = Path(__file__).resolve().parent.parent
    if _has_project_markers(package_parent):
        return package_parent

    raise FileNotFoundError(
        "Could not find EmberForge project root. Set EMBERFORGE_ROOT or run from the repo."
    )