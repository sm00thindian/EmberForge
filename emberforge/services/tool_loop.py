"""OpenAI-compatible tool-calling loop for chat completions."""

from __future__ import annotations

from typing import Any

import httpx

from emberforge.errors import llm_error
from emberforge.http.retry import is_retryable_status, post_with_retry
from emberforge.services.llm import LlmConfig
from emberforge.services.tools import ToolService
from emberforge.settings import Settings


def _extract_message(data: dict[str, Any]) -> dict[str, Any]:
    return data["choices"][0]["message"]


async def complete_with_tools(
    *,
    settings: Settings,
    llm_config: LlmConfig,
    messages: list[dict[str, Any]],
    temperature: float,
    tool_service: ToolService,
    request_id: str,
    max_tokens: int | None = None,
) -> str:
    """
    Run chat completions with tool auto-invocation until the model returns text
    or max rounds are exhausted.
    """
    headers = {
        "Authorization": f"Bearer {llm_config.api_key}",
        "Content-Type": "application/json",
    }
    tools = tool_service.definitions
    working_messages = list(messages)
    max_rounds = settings.tools_max_rounds
    resolved_max_tokens = max_tokens if max_tokens is not None else settings.xai_max_tokens

    async with httpx.AsyncClient(timeout=settings.xai_timeout_seconds) as client:
        for _ in range(max_rounds):
            payload: dict[str, Any] = {
                "model": llm_config.model,
                "messages": working_messages,
                "temperature": temperature,
                "max_tokens": resolved_max_tokens,
            }
            if tools:
                payload["tools"] = tools
                payload["tool_choice"] = "auto"

            try:
                response = await post_with_retry(
                    client,
                    llm_config.api_url,
                    max_retries=settings.xai_max_retries,
                    base_delay_seconds=settings.xai_retry_base_seconds,
                    json=payload,
                    headers=headers,
                )
            except httpx.TimeoutException as exc:
                raise llm_error("LLM request timed out", retryable=True, request_id=request_id) from exc
            except httpx.TransportError as exc:
                raise llm_error("LLM service unreachable", retryable=True, request_id=request_id) from exc

            if response.status_code >= 400:
                raise llm_error(
                    f"LLM returned HTTP {response.status_code}",
                    retryable=is_retryable_status(response.status_code),
                    request_id=request_id,
                )

            try:
                data = response.json()
                message = _extract_message(data)
            except (KeyError, IndexError, TypeError, ValueError) as exc:
                raise llm_error("Invalid response from LLM", retryable=False, request_id=request_id) from exc

            tool_calls = message.get("tool_calls") or []
            if not tool_calls:
                content = message.get("content") or ""
                return str(content).strip()

            working_messages.append(message)
            for tool_call in tool_calls:
                function = tool_call.get("function", {})
                name = function.get("name", "")
                arguments = function.get("arguments", "{}")
                result = tool_service.execute(name, arguments)
                working_messages.append(
                    {
                        "role": "tool",
                        "tool_call_id": tool_call.get("id", ""),
                        "content": result,
                    }
                )

    raise llm_error(
        "LLM exceeded maximum tool rounds without a final reply",
        retryable=False,
        request_id=request_id,
    )