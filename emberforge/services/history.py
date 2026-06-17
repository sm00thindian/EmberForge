"""In-memory multi-turn conversation history for voice sessions."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from threading import Lock


@dataclass
class _SessionState:
    persona_id: str
    turns: list[tuple[str, str]] = field(default_factory=list)
    updated_at: float = field(default_factory=time.time)


class ConversationHistoryStore:
    """Per-session user/assistant turns, scoped by persona."""

    def __init__(self, *, max_turns: int = 20, ttl_seconds: float = 86_400.0) -> None:
        self._max_turns = max(1, max_turns)
        self._ttl_seconds = ttl_seconds
        self._sessions: dict[str, _SessionState] = {}
        self._lock = Lock()

    def prepare_messages(
        self,
        session_id: str,
        persona_id: str,
        *,
        clear: bool = False,
    ) -> list[dict[str, str]]:
        """Return prior turns as LLM messages; reset when persona changes or clear is set."""
        now = time.time()
        with self._lock:
            self._purge_expired_locked(now)
            state = self._sessions.get(session_id)
            if clear or state is None or state.persona_id != persona_id:
                self._sessions[session_id] = _SessionState(persona_id=persona_id, updated_at=now)
                return []
            state.updated_at = now
            return self._turns_to_messages(state.turns)

    def record_turn(
        self,
        session_id: str,
        persona_id: str,
        user_message: str,
        assistant_message: str,
    ) -> int:
        """Append a completed turn and return the turn count for this session."""
        now = time.time()
        with self._lock:
            self._purge_expired_locked(now)
            state = self._sessions.get(session_id)
            if state is None or state.persona_id != persona_id:
                state = _SessionState(persona_id=persona_id, updated_at=now)
                self._sessions[session_id] = state
            state.turns.append((user_message, assistant_message))
            if len(state.turns) > self._max_turns:
                state.turns = state.turns[-self._max_turns :]
            state.updated_at = now
            return len(state.turns)

    def turn_count(self, session_id: str) -> int:
        with self._lock:
            state = self._sessions.get(session_id)
            return len(state.turns) if state else 0

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def reset(self) -> None:
        with self._lock:
            self._sessions.clear()

    def _turns_to_messages(self, turns: list[tuple[str, str]]) -> list[dict[str, str]]:
        messages: list[dict[str, str]] = []
        for user_text, assistant_text in turns:
            messages.append({"role": "user", "content": user_text})
            messages.append({"role": "assistant", "content": assistant_text})
        return messages

    def _purge_expired_locked(self, now: float) -> None:
        expired = [
            session_id
            for session_id, state in self._sessions.items()
            if now - state.updated_at > self._ttl_seconds
        ]
        for session_id in expired:
            self._sessions.pop(session_id, None)


_MULTI_TURN_INSTRUCTION = """

## Active conversation (voice session)
You are continuing an ongoing thread — not starting a new chat.
- Respond directly to the user's **latest** message above all else.
- Use earlier turns only when needed (names, topics, decisions already established).
- Do **not** repeat greetings, day-openers, or recap phrases from prior turns unless the user greets you again.
- Do **not** echo your previous opening lines (e.g. if you said "Morning" once, never say it again this session).
- Skip filler openers when the conversation is already underway; vary naturally.
"""


def build_llm_messages(
    system_prompt: str,
    history: list[dict[str, str]],
    user_message: str,
) -> list[dict[str, str]]:
    system_content = system_prompt
    if history:
        system_content = f"{system_prompt.rstrip()}{_MULTI_TURN_INSTRUCTION}"

    messages = [{"role": "system", "content": system_content}]
    messages.extend(history)
    messages.append({"role": "user", "content": user_message})
    return messages