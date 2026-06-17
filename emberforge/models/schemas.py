"""Pydantic schemas for HTTP APIs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    persona: str = "ember"
    temperature: float | None = None
    model: str | None = Field(
        default=None,
        description="LLM model id override (e.g. grok-3-latest, gpt-4o). Falls back to persona or EMBER_LLM_MODEL.",
    )
    session_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Stable id for multi-turn context (reuse across PTT turns).",
    )
    clear_history: bool = Field(
        default=False,
        description="Clear prior turns for this session before processing the message.",
    )
    synthesize_audio: bool = Field(
        default=False,
        description="Return playable audio in voice.audio_base64 when server TTS is available.",
    )
    play_audio: bool = Field(
        default=False,
        description="Play speech on the hub (e.g. macOS say) when no audio bytes are returned.",
    )


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    persona: str
    persona_name: str
    voice: dict
    model: str
    request_id: Optional[str] = None
    session_id: Optional[str] = None
    history_turns: int = 0


class DeviceTextRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    persona: str = "ember"
    model: str | None = None
    device_id: Optional[str] = None
    request_id: Optional[str] = None
    session_id: Optional[str] = Field(
        default=None,
        max_length=128,
        description="Conversation session; defaults to device_id when omitted.",
    )
    clear_history: bool = False


class DevicePairConfirmRequest(BaseModel):
    code: str = Field(..., min_length=4, max_length=12)
    device_id: str = Field(..., min_length=1, max_length=128)
    name: Optional[str] = Field(default=None, max_length=128)