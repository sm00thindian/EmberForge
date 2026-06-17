"""Mac voice client tests."""

from __future__ import annotations

from emberforge.client.mac_voice import parse_quoted_prompt


def test_parse_quoted_prompt_double_quotes():
    assert parse_quoted_prompt('"Hal, close the cabin doors"') == "Hal, close the cabin doors"


def test_parse_quoted_prompt_single_quotes():
    assert parse_quoted_prompt("'Open the pod bay doors'") == "Open the pod bay doors"


def test_parse_quoted_prompt_ignores_commands():
    assert parse_quoted_prompt("persona hal_9000") is None
    assert parse_quoted_prompt("") is None
    assert parse_quoted_prompt('""') is None


def test_parse_quoted_prompt_preserves_case():
    assert parse_quoted_prompt('"Hello HAL"') == "Hello HAL"