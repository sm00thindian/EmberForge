"""Pydantic schemas for HTTP APIs."""

from __future__ import annotations

from typing import Optional

from pydantic import BaseModel, Field

class ChatRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    persona: str = "ember"
    temperature: float | None = None


class ChatResponse(BaseModel):
    response: str
    timestamp: str
    persona: str
    persona_name: str
    voice: dict
    request_id: Optional[str] = None


class DeviceTextRequest(BaseModel):
    message: str = Field(..., min_length=1, max_length=4000)
    persona: str = "ember"
    device_id: Optional[str] = None
    request_id: Optional[str] = None