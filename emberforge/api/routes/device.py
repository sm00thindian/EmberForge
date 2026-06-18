"""Stable device API for consumer-grade hardware."""

from __future__ import annotations

from typing import Optional

from fastapi import APIRouter, Depends, File, Form, UploadFile

from emberforge.api.deps import verify_device
from emberforge.context import ensure_request_id, get_request_id
from emberforge.errors import audio_invalid, audio_too_large, stt_unavailable
from emberforge.models.schemas import DevicePairConfirmRequest, DeviceTextRequest
from emberforge.security.runtime import get_security_state
from emberforge.services.conversation import ConversationResult
from emberforge.services.converse import ConverseService
from emberforge.hub.runtime import build_hub
from emberforge.hub.tenancy import scoped_session_id
from emberforge.settings import Settings

DEVICE_AUTH = [Depends(verify_device)]


def conversation_payload(result: ConversationResult) -> dict:
    payload = {
        "request_id": result.request_id,
        "transcript": result.transcript,
        "response_text": result.response_text,
        "persona": {
            "id": result.persona_id,
            "name": result.persona_name,
        },
        "voice": result.voice,
        "display": {
            "title": result.persona_name,
            "lines": result.display_lines,
        },
        "timestamp": result.timestamp,
    }
    if result.session_id:
        payload["session_id"] = result.session_id
    if result.history_turns:
        payload["history_turns"] = result.history_turns
    return payload


def create_device_routers(
    settings: Settings,
    converse: ConverseService,
) -> tuple[APIRouter, APIRouter, APIRouter]:
    pair_router = APIRouter(prefix="/device/v1", tags=["device"])
    meta_router = APIRouter(
        prefix="/device/v1",
        tags=["device"],
        dependencies=DEVICE_AUTH,
    )
    audio_router = APIRouter(
        prefix="/device/v1",
        tags=["device"],
        dependencies=DEVICE_AUTH,
    )
    hub = build_hub(settings)

    @meta_router.get("/capabilities")
    async def device_capabilities():
        return {
            "api_version": settings.device_api_version,
            "service": "emberforge",
            "hub": hub.as_capabilities(),
            "features": {
                "personas": True,
                "text_converse": True,
                "audio_converse": converse.stt_available(),
                "server_tts": converse.server_tts_available(),
                "custom_voices": converse.server_tts_available(),
                "offline_mode": False,
            },
            "tts": {
                "formats": ["mp3"] if converse.server_tts_available() else [],
                "fallback_enabled": settings.device_tts_fallback,
            },
            "audio": {
                "input_formats": ["wav"],
                "wav_encoding": "pcm_s16le",
                "preferred_sample_rate": 16000,
                "max_upload_bytes": settings.max_audio_bytes,
            },
            "llm": {
                "default_model": settings.llm_model,
                "api": "openai_chat_completions",
            },
            "persona_selection": ["api_param", "device_config"],
            "auth": {
                "required": settings.device_auth_required,
                "scheme": "bearer",
                "pairing": "POST /admin/v1/pair/code then POST /device/v1/pair/confirm",
            },
            "admin_auth": {
                "remote_production": settings.is_production,
                "totp_session": bool(settings.admin_totp_secret),
                "static_token": bool(settings.admin_token),
            },
        }

    @meta_router.get("/personas")
    async def device_personas():
        return {
            "default": settings.default_persona_id,
            "personas": [persona.to_device_dict() for persona in converse.personas.values()],
        }

    @pair_router.post("/pair/confirm")
    async def device_pair_confirm(request: DevicePairConfirmRequest):
        pairing = get_security_state()["pairing_codes"]
        if not pairing.consume(request.code):
            from fastapi import HTTPException

            raise HTTPException(status_code=400, detail="Invalid or expired pairing code")

        registry = get_security_state()["device_registry"]
        token = registry.pair_device(device_id=request.device_id, name=request.name)
        return {
            "device_id": request.device_id,
            "device_token": token,
            "message": "Save this token on the device — it will not be shown again.",
        }

    @meta_router.post("/converse/text")
    async def device_converse_text(request: DeviceTextRequest):
        session_id = scoped_session_id(
            hub.tenant_key,
            request.session_id or request.device_id or "",
        )
        result = await converse.converse_text(
            request.persona,
            request.message,
            model=request.model,
            request_id=request.request_id,
            session_id=session_id,
            clear_history=request.clear_history,
            synthesize_audio=True,
        )
        return conversation_payload(result)

    @audio_router.post("/converse")
    async def device_converse_audio(
        audio: UploadFile = File(...),
        persona: str = Form(default=None),
        device_id: Optional[str] = Form(default=None),
        request_id: Optional[str] = Form(default=None),
    ):
        if not converse.stt_available():
            raise stt_unavailable(
                "Server STT unavailable. Install faster-whisper.",
                get_request_id(),
            )

        persona_id = persona or settings.default_persona_id
        resolved_request_id = ensure_request_id(request_id)

        audio_bytes = await audio.read()
        if not audio_bytes:
            raise audio_invalid("Empty audio upload", request_id=resolved_request_id)
        if len(audio_bytes) > settings.max_audio_bytes:
            raise audio_too_large(request_id=resolved_request_id)

        session_id = scoped_session_id(hub.tenant_key, device_id or "")
        result = await converse.converse_audio(
            persona_id,
            audio_bytes,
            request_id=resolved_request_id,
            session_id=session_id,
            synthesize_audio=True,
        )

        payload = conversation_payload(result)
        payload["device_id"] = device_id
        return payload

    return pair_router, meta_router, audio_router