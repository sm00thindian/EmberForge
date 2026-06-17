"""Multi-turn conversation memory tests."""

from __future__ import annotations

from unittest.mock import AsyncMock, patch

import httpx
import pytest

from emberforge.services.conversation import generate_reply
from emberforge.services.history import ConversationHistoryStore, build_llm_messages
from emberforge.services.personas import get_persona
from emberforge.settings import Settings


def test_build_llm_messages_orders_system_history_and_user():
    history = [
        {"role": "user", "content": "Hi"},
        {"role": "assistant", "content": "Hello"},
    ]
    messages = build_llm_messages("You are Ember.", history, "Follow up")
    assert messages[0]["role"] == "system"
    assert "latest" in messages[0]["content"].lower()
    assert "Do **not** repeat greetings" in messages[0]["content"]
    assert messages[-1] == {"role": "user", "content": "Follow up"}
    assert len(messages) == 4


def test_build_llm_messages_omits_continuation_on_first_turn():
    messages = build_llm_messages("You are Ember.", [], "Hello")
    assert messages[0]["content"] == "You are Ember."


def test_history_store_records_and_trims_turns():
    store = ConversationHistoryStore(max_turns=2, ttl_seconds=3600)
    session = "mac-test"

    store.record_turn(session, "ember", "one", "reply one")
    store.record_turn(session, "ember", "two", "reply two")
    store.record_turn(session, "ember", "three", "reply three")

    messages = store.prepare_messages(session, "ember")
    assert len(messages) == 4
    assert messages[0]["content"] == "two"
    assert messages[-1]["content"] == "reply three"


def test_history_store_resets_on_persona_change():
    store = ConversationHistoryStore()
    session = "device-1"

    store.record_turn(session, "ember", "Hi", "Hello")
    messages = store.prepare_messages(session, "hal_9000")
    assert messages == []


@pytest.mark.asyncio
async def test_generate_reply_sends_prior_turns_to_llm(test_settings: Settings):
    store = ConversationHistoryStore(max_turns=10)
    ember = get_persona("ember", settings=test_settings)
    payloads: list[dict] = []

    async def fake_post(client, url, **kwargs):
        payloads.append(kwargs["json"])
        turn = len(payloads)
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": f"Reply {turn}"}}]},
            request=httpx.Request("POST", url),
        )

    with patch("emberforge.services.conversation.post_with_retry", AsyncMock(side_effect=fake_post)):
        first = await generate_reply(
            ember,
            "Remember my name is Kim.",
            settings=test_settings,
            session_id="sess-1",
            history_store=store,
        )
        second = await generate_reply(
            ember,
            "What is my name?",
            settings=test_settings,
            session_id="sess-1",
            history_store=store,
        )

    assert first.history_turns == 1
    assert second.history_turns == 2

    second_messages = payloads[1]["messages"]
    assert second_messages[1]["content"] == "Remember my name is Kim."
    assert second_messages[2]["content"] == "Reply 1"
    assert second_messages[3]["content"] == "What is my name?"


@pytest.mark.asyncio
async def test_generate_reply_clear_history(test_settings: Settings):
    store = ConversationHistoryStore()
    ember = get_persona("ember", settings=test_settings)

    async def fake_post(client, url, **kwargs):
        return httpx.Response(
            200,
            json={"choices": [{"message": {"content": "OK"}}]},
            request=httpx.Request("POST", url),
        )

    with patch("emberforge.services.conversation.post_with_retry", AsyncMock(side_effect=fake_post)):
        await generate_reply(
            ember,
            "First",
            settings=test_settings,
            session_id="sess-2",
            history_store=store,
        )
        result = await generate_reply(
            ember,
            "Fresh start",
            settings=test_settings,
            session_id="sess-2",
            history_store=store,
            clear_history=True,
        )

    assert result.history_turns == 1
    assert store.turn_count("sess-2") == 1