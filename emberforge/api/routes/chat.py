"""Mac and developer chat routes."""

from __future__ import annotations

from fastapi import APIRouter

from emberforge.context import get_request_id
from emberforge.models.schemas import ChatRequest, ChatResponse
from emberforge.services.conversation import ConversationResult
from emberforge.services.converse import ConverseService
from emberforge.settings import Settings


def chat_from_result(result: ConversationResult) -> ChatResponse:
    return ChatResponse(
        response=result.response_text,
        timestamp=result.timestamp,
        persona=result.persona_id,
        persona_name=result.persona_name,
        voice=result.voice,
        request_id=result.request_id,
    )


def create_chat_router(settings: Settings, converse: ConverseService) -> APIRouter:
    router = APIRouter(tags=["chat"])
    personas = converse.personas

    @router.get("/personas")
    async def list_personas():
        return {
            "default": settings.default_persona_id,
            "personas": [persona.to_public_dict() for persona in personas.values()],
        }

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest):
        result = await converse.converse_text(
            request.persona,
            request.message,
            temperature=request.temperature,
            request_id=get_request_id() or None,
        )
        return chat_from_result(result)

    return router