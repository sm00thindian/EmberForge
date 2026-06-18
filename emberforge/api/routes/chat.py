"""Mac and developer chat routes."""

from __future__ import annotations

from fastapi import APIRouter, BackgroundTasks, Depends

from emberforge.api.deps import verify_admin
from emberforge.context import get_request_id
from emberforge.models.schemas import ChatRequest, ChatResponse
from emberforge.services.conversation import ConversationResult
from emberforge.services.converse import ConverseService
from emberforge.services.voice.registry import get_tts_provider
from emberforge.settings import Settings


async def _play_hub_speech(converse: ConverseService, persona_id: str, text: str) -> None:
    """Play macOS say after the chat response has been sent to the client."""
    persona = converse.resolve_persona(persona_id)
    tts = get_tts_provider(persona.voice, converse.settings)
    await tts.synthesize(text, persona.voice)


def chat_from_result(result: ConversationResult) -> ChatResponse:
    return ChatResponse(
        response=result.response_text,
        timestamp=result.timestamp,
        persona=result.persona_id,
        persona_name=result.persona_name,
        voice=result.voice,
        model=result.model,
        request_id=result.request_id,
        session_id=result.session_id,
        history_turns=result.history_turns,
    )


def create_chat_router(settings: Settings, converse: ConverseService) -> APIRouter:
    router = APIRouter(tags=["chat"], dependencies=[Depends(verify_admin)])
    personas = converse.personas

    @router.get("/personas")
    async def list_personas():
        return {
            "default": settings.default_persona_id,
            "personas": [persona.to_public_dict() for persona in personas.values()],
        }

    @router.post("/chat", response_model=ChatResponse)
    async def chat(request: ChatRequest, background_tasks: BackgroundTasks):
        # Hub speak (macOS say) blocks for the full utterance — defer so text renders first.
        defer_hub_playback = request.play_audio and not request.synthesize_audio
        result = await converse.converse_text(
            request.persona,
            request.message,
            temperature=request.temperature,
            model=request.model,
            request_id=get_request_id() or None,
            session_id=request.session_id,
            clear_history=request.clear_history,
            synthesize_audio=request.synthesize_audio,
            play_audio=request.play_audio and not defer_hub_playback,
        )
        if defer_hub_playback:
            background_tasks.add_task(
                _play_hub_speech,
                converse,
                request.persona,
                result.response_text,
            )
        return chat_from_result(result)

    return router