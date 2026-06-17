"""Helpers for /device/v1/ JSON Schema contract tests."""

from __future__ import annotations

import json
from pathlib import Path

import jsonschema
from jsonschema import Draft202012Validator

SCHEMA_ROOT = Path(__file__).resolve().parents[1] / "device" / "schemas" / "v1"


def load_schema(name: str) -> dict:
    path = SCHEMA_ROOT / name
    return json.loads(path.read_text(encoding="utf-8"))


def assert_matches_schema(instance: dict, schema_name: str) -> None:
    schema = load_schema(schema_name)
    validator = Draft202012Validator(schema)
    errors = sorted(validator.iter_errors(instance), key=lambda err: err.path)
    if errors:
        details = "; ".join(f"{list(err.path)}: {err.message}" for err in errors)
        raise AssertionError(f"Response does not match {schema_name}: {details}")
    jsonschema.validate(instance=instance, schema=schema)