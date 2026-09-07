"""
Async Groq chat-completions client.

Groq exposes an OpenAI-compatible surface, so this speaks the same wire format:
`messages`, `tools` (function calling), and `response_format`. Failures raise
typed errors instead of silently substituting canned text -- a masked outage
that returns plausible-looking content is worse than a visible 502.
"""
from __future__ import annotations

import asyncio
import json
import random
from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence

import httpx

from ..core.config.settings import settings
from ..core.logging.logger import app_logger
from .errors import (
    LLMBadRequestError,
    LLMNotConfiguredError,
    LLMRateLimitError,
    LLMResponseFormatError,
    LLMServerError,
)
from .ratelimit import estimate_tokens, get_rate_limiter


#: Models observed to reject `response_format: json_object`. Populated at
#: runtime on first rejection, so no hardcoded capability table goes stale.
_NO_JSON_MODE: set[str] = set()


@dataclass
class ToolCall:
    id: str
    name: str
    arguments: Dict[str, Any]


@dataclass
class Usage:
    prompt_tokens: int = 0
    completion_tokens: int = 0

    @property
    def total_tokens(self) -> int:
        return self.prompt_tokens + self.completion_tokens

    def __add__(self, other: "Usage") -> "Usage":
        return Usage(
            self.prompt_tokens + other.prompt_tokens,
            self.completion_tokens + other.completion_tokens,
        )


@dataclass
class LLMResponse:
    content: str
    tool_calls: List[ToolCall] = field(default_factory=list)
    finish_reason: str = "stop"
    usage: Usage = field(default_factory=Usage)
    model: str = ""

    @property
    def raw_message(self) -> Dict[str, Any]:
        """The assistant message in wire format, for appending to history."""
        message: Dict[str, Any] = {"role": "assistant", "content": self.content or ""}
        if self.tool_calls:
            message["tool_calls"] = [
                {
                    "id": call.id,
                    "type": "function",
                    "function": {
                        "name": call.name,
                        "arguments": json.dumps(call.arguments),
                    },
                }
                for call in self.tool_calls
            ]
        return message


class LLMClient:
    """Thin, retrying wrapper around Groq's chat-completions endpoint."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        base_url: Optional[str] = None,
        default_model: Optional[str] = None,
        timeout: Optional[float] = None,
        max_retries: Optional[int] = None,
    ):
        self._api_key = (api_key or settings.GROQ_API_KEY or "").strip().strip('"').strip("'")
        self._base_url = (base_url or settings.GROQ_BASE_URL).rstrip("/")
        self._default_model = default_model or settings.GROQ_MODEL
        self._timeout = timeout or settings.LLM_TIMEOUT_SECONDS
        self._max_retries = settings.LLM_MAX_RETRIES if max_retries is None else max_retries
        self._client: Optional[httpx.AsyncClient] = None

    async def __aenter__(self) -> "LLMClient":
        self._client = httpx.AsyncClient(timeout=self._timeout)
        return self

    async def __aexit__(self, *_exc) -> None:
        if self._client is not None:
            await self._client.aclose()
            self._client = None

    @property
    def configured(self) -> bool:
        return bool(self._api_key) and not self._api_key.startswith("gsk_your")

    async def complete(
        self,
        messages: Sequence[Dict[str, Any]],
        *,
        model: Optional[str] = None,
        tools: Optional[List[Dict[str, Any]]] = None,
        tool_choice: Optional[str] = None,
        temperature: float = 0.4,
        max_tokens: int = 2048,
        json_mode: bool = False,
    ) -> LLMResponse:
        if not self.configured:
            raise LLMNotConfiguredError(
                "GROQ_API_KEY is not set. Add it to backend/.env for local runs, "
                "or to the project's environment variables when deploying."
            )

        target_model = model or self._default_model
        payload: Dict[str, Any] = {
            "model": target_model,
            "messages": list(messages),
            "temperature": temperature,
            "max_tokens": max_tokens,
        }
        if tools:
            payload["tools"] = tools
            payload["tool_choice"] = tool_choice or "auto"

        # Not every model on Groq accepts `response_format`. Rather than forgo a
        # whole model (and its separate token budget), request JSON mode
        # optimistically and fall back to schema-in-prompt on rejection. The
        # response parser tolerates prose-wrapped JSON either way.
        want_json = json_mode and target_model not in _NO_JSON_MODE
        if want_json:
            payload["response_format"] = {"type": "json_object"}

        # Budgets are per model and include a per-day ceiling, so one model can
        # be spent while its siblings are untouched. Rather than fail the whole
        # run, exhaustion falls through to the next model that is still viable.
        candidates = [target_model] + [
            alternative
            for alternative in (settings.GROQ_MODEL, settings.GROQ_FAST_MODEL, settings.GROQ_ALT_MODEL)
            if alternative and alternative != target_model
        ]

        last_error: Optional[Exception] = None
        for index, candidate in enumerate(candidates):
            if index > 0:
                app_logger.warning(
                    "Model budget exhausted; falling back",
                    exhausted=candidates[index - 1],
                    fallback=candidate,
                )
                payload["model"] = candidate
                if candidate in _NO_JSON_MODE:
                    payload.pop("response_format", None)
                    want_json = False
            try:
                return await self._complete_with_retries(payload, candidate, want_json)
            except LLMRateLimitError as exc:
                last_error = exc
                continue

        raise last_error if last_error else LLMServerError("LLM call failed with no error recorded")

    async def _complete_with_retries(
        self, payload: Dict[str, Any], model_name: str, want_json: bool
    ) -> LLMResponse:
        """Retry loop for one model. Raises LLMRateLimitError once spent."""
        bucket = get_rate_limiter().bucket(model_name)
        estimated = _estimate_request_tokens(payload)

        last_error: Optional[Exception] = None
        for attempt in range(self._max_retries + 1):
            try:
                await bucket.acquire(estimated)
                return self._parse(await self._post(payload, bucket))
            except LLMBadRequestError as exc:
                # Only an actual complaint about `response_format` means the
                # model lacks JSON mode. A stray tool call or an unvalidatable
                # body is the model misbehaving, and blacklisting JSON mode over
                # it would silently degrade every later call to that model.
                unsupported = "response_format" in str(exc) and "json_validate_failed" not in str(exc)
                if want_json and unsupported and "response_format" in payload:
                    app_logger.info(
                        "Model does not support JSON mode; falling back to schema-in-prompt",
                        model=model_name,
                    )
                    _NO_JSON_MODE.add(model_name)
                    payload.pop("response_format", None)
                    want_json = False
                    continue
                raise
            except (LLMRateLimitError, LLMServerError) as exc:
                last_error = exc
                if attempt == self._max_retries:
                    break
                retry_after = getattr(exc, "retry_after", None)
                requested = retry_after or (
                    settings.LLM_RETRY_BASE_DELAY * (2**attempt) + random.uniform(0, 0.25)
                )
                # Honour the provider's Retry-After, but cap it. When a budget is
                # genuinely exhausted Groq can ask for several minutes; sleeping
                # that long (times the retry count) turns a request into a
                # multi-minute hang. A prompt, honest failure is more useful to a
                # caller than an indefinite wait.
                delay = min(requested, settings.LLM_MAX_RETRY_DELAY)
                app_logger.warning(
                    "LLM call failed, retrying",
                    model=model_name,
                    attempt=attempt + 1,
                    max_retries=self._max_retries,
                    retry_after_header=retry_after,
                    delay_seconds=round(delay, 2),
                    capped=delay < requested,
                    error=str(exc)[:200],
                )
                await asyncio.sleep(delay)

        raise last_error if last_error else LLMServerError("LLM call failed with no error recorded")

    async def _post(self, payload: Dict[str, Any], bucket: Any) -> Dict[str, Any]:
        client = self._client
        # Support use outside `async with` by falling back to a per-call client.
        if client is None:
            async with httpx.AsyncClient(timeout=self._timeout) as scoped:
                response = await self._send(scoped, payload, bucket)
        else:
            response = await self._send(client, payload, bucket)
        return response

    async def _send(
        self, client: httpx.AsyncClient, payload: Dict[str, Any], bucket: Any
    ) -> Dict[str, Any]:
        try:
            response = await client.post(
                f"{self._base_url}/chat/completions",
                headers={
                    "Authorization": f"Bearer {self._api_key}",
                    "Content-Type": "application/json",
                },
                json=payload,
            )
        except httpx.TimeoutException as exc:
            raise LLMServerError(f"LLM request timed out after {self._timeout}s") from exc
        except httpx.HTTPError as exc:
            raise LLMServerError(f"LLM transport error: {exc}") from exc

        if response.status_code >= 400:
            self._raise_for_error(response)

        try:
            body = response.json()
        except ValueError as exc:
            raise LLMResponseFormatError("Provider returned a non-JSON body") from exc

        actual = int((body.get("usage") or {}).get("total_tokens") or 0)
        bucket.observe(response.headers, actual)
        return body

    @staticmethod
    def _raise_for_error(response: httpx.Response) -> None:
        """Classify a 4xx/5xx.

        Groq reports a tokens-per-minute overage as **413** with
        `code: rate_limit_exceeded`, not 429. Classifying purely on status code
        would make an entirely transient condition look like a permanently
        malformed request, so the error body decides.
        """
        body = response.text[:600]
        code = ""
        error_type = ""
        try:
            error = (response.json() or {}).get("error") or {}
            code = str(error.get("code") or "")
            error_type = str(error.get("type") or "")
        except ValueError:
            pass

        rate_limited = (
            response.status_code == 429
            or code == "rate_limit_exceeded"
            or error_type in {"tokens", "requests"}
        )

        if rate_limited:
            retry_after = response.headers.get("retry-after")
            parsed: Optional[float] = None
            if retry_after and retry_after.replace(".", "", 1).isdigit():
                parsed = float(retry_after)
            raise LLMRateLimitError(
                f"Token/request budget exceeded for this model ({response.status_code}): {body}",
                retry_after=parsed,
            )

        if response.status_code >= 500:
            raise LLMServerError(f"Provider error {response.status_code}: {body}")

        raise LLMBadRequestError(f"Provider rejected request ({response.status_code}): {body}")

    @staticmethod
    def _parse(data: Dict[str, Any]) -> LLMResponse:
        choices = data.get("choices")
        if not choices:
            raise LLMResponseFormatError(f"Response contained no choices: {str(data)[:300]}")

        choice = choices[0]
        message = choice.get("message") or {}
        raw_usage = data.get("usage") or {}

        tool_calls: List[ToolCall] = []
        for call in message.get("tool_calls") or []:
            function = call.get("function") or {}
            raw_args = function.get("arguments") or "{}"
            try:
                parsed_args = json.loads(raw_args) if isinstance(raw_args, str) else dict(raw_args)
            except json.JSONDecodeError:
                # A malformed argument blob is the model's mistake, not a transport
                # failure. Surface it to the agent loop as a tool error instead of
                # crashing the whole run.
                parsed_args = {"__malformed_arguments__": str(raw_args)[:500]}
            tool_calls.append(
                ToolCall(
                    id=call.get("id") or f"call_{len(tool_calls)}",
                    name=function.get("name") or "",
                    arguments=parsed_args,
                )
            )

        return LLMResponse(
            content=message.get("content") or "",
            tool_calls=tool_calls,
            finish_reason=choice.get("finish_reason") or "stop",
            usage=Usage(
                prompt_tokens=int(raw_usage.get("prompt_tokens") or 0),
                completion_tokens=int(raw_usage.get("completion_tokens") or 0),
            ),
            model=str(data.get("model") or ""),
        )


def _estimate_request_tokens(payload: Dict[str, Any]) -> int:
    """Prompt + reserved completion tokens, which is what the TPM budget counts."""
    text_parts: List[str] = []
    for message in payload.get("messages") or []:
        content = message.get("content")
        if isinstance(content, str):
            text_parts.append(content)
        for call in message.get("tool_calls") or []:
            text_parts.append(json.dumps(call))
    for tool in payload.get("tools") or []:
        text_parts.append(json.dumps(tool))

    prompt_tokens = estimate_tokens("".join(text_parts))
    return prompt_tokens + int(payload.get("max_tokens") or 0)
