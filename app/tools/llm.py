"""LLM helper (Google Gemini) with retries and gentle rate limiting."""

from __future__ import annotations

import json
import re
import threading
import time
from typing import Any

from langchain_core.messages import HumanMessage, SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI

from app.config import get_settings

# Parallel agents share one process — serialize Gemini calls to stay under free RPM.
_llm_lock = threading.Lock()
_last_call_at = 0.0
_MIN_INTERVAL_SEC = 1.2


def get_llm(temperature: float = 0.2) -> ChatGoogleGenerativeAI:
    settings = get_settings()
    if not settings.google_api_key:
        raise RuntimeError(
            "GOOGLE_API_KEY is required. Set it in .env — https://aistudio.google.com/apikey"
        )
    return ChatGoogleGenerativeAI(
        model=settings.llm_model,
        google_api_key=settings.google_api_key,
        temperature=temperature,
    )


def extract_json(text: str) -> dict[str, Any] | list[Any]:
    """Parse JSON from model output, tolerating markdown fences."""
    text = text.strip()
    fence = re.search(r"```(?:json)?\s*([\s\S]*?)```", text)
    if fence:
        text = fence.group(1).strip()
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        match = re.search(r"(\{[\s\S]*\}|\[[\s\S]*\])", text)
        if match:
            return json.loads(match.group(1))
        raise


def _is_quota_error(exc: BaseException) -> bool:
    text = str(exc).lower()
    return any(
        token in text
        for token in (
            "resource_exhausted",
            "429",
            "quota",
            "rate limit",
            "rate_limit",
        )
    )


def _friendly_llm_error(exc: BaseException) -> str:
    if _is_quota_error(exc):
        return (
            "Gemini quota exceeded for the current model. "
            "Wait a minute, or set LLM_MODEL=gemini-flash-lite-latest in .env and retry."
        )
    message = str(exc)
    if len(message) > 180:
        message = message[:177] + "..."
    return message


def llm_json(
    system: str,
    user: str,
    temperature: float = 0.2,
    max_retries: int = 4,
) -> dict[str, Any] | list[Any]:
    llm = get_llm(temperature=temperature)
    last_error: BaseException | None = None

    for attempt in range(max_retries):
        with _llm_lock:
            global _last_call_at
            wait = _MIN_INTERVAL_SEC - (time.monotonic() - _last_call_at)
            if wait > 0:
                time.sleep(wait)
            try:
                response = llm.invoke(
                    [SystemMessage(content=system), HumanMessage(content=user)]
                )
                _last_call_at = time.monotonic()
            except Exception as exc:
                last_error = exc
                _last_call_at = time.monotonic()
                if _is_quota_error(exc) and attempt < max_retries - 1:
                    # Honor typical free-tier cooldown without hanging forever.
                    time.sleep(min(20.0, 4.0 * (attempt + 1)))
                    continue
                raise RuntimeError(_friendly_llm_error(exc)) from exc

        content = response.content
        if isinstance(content, list):
            content = "".join(
                block.get("text", "") if isinstance(block, dict) else str(block)
                for block in content
            )
        try:
            return extract_json(str(content))
        except Exception as exc:
            last_error = exc
            if attempt < max_retries - 1:
                continue
            raise RuntimeError(f"Model returned invalid JSON: {exc}") from exc

    raise RuntimeError(_friendly_llm_error(last_error or RuntimeError("LLM call failed")))
