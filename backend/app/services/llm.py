
"""LLM client with Gemini primary and Groq fallback.

Features:
- Gemini/OpenAI primary provider with optional Groq fallback.
- Independent hourly limits and cooldowns per provider.
- Bounded retries for temporary provider failures.
- JSON-only output with validation.
- API keys are never logged or included in error messages.
"""

from __future__ import annotations

import json
import logging
import re
import threading
import time
from datetime import datetime, timezone
from email.utils import parsedate_to_datetime

import requests

from app.config import settings

logger = logging.getLogger(__name__)

DEFAULT_MODELS = {
    "gemini": "gemini-2.5-flash",
    "openai": "gpt-4o-mini",
    "groq": "openai/gpt-oss-20b",
}

GEMINI_URL = (
    "https://generativelanguage.googleapis.com/v1beta/"
    "models/{model}:generateContent"
)
OPENAI_URL = "https://api.openai.com/v1/chat/completions"
GROQ_URL = "https://api.groq.com/openai/v1/chat/completions"

MAX_ATTEMPTS = 3
BASE_RETRY_DELAY = 2.0
MAX_RETRY_DELAY = 30.0

RETRYABLE_STATUS_CODES = {429, 500, 502, 503, 504}


class LLMError(Exception):
    """The provider call failed or returned unusable data."""


class LLMUnavailable(LLMError):
    """Not configured, cooling down, or hourly request limit reached."""


class LLMHTTPError(LLMError):
    """An HTTP error from an LLM provider."""

    def __init__(self, provider: str, status_code: int, retry_after=None):
        self.provider = provider
        self.status_code = status_code
        self.retry_after = retry_after
        super().__init__(f"{provider} HTTP {status_code}")


_lock = threading.Lock()
_cooldowns = {"gemini": 0.0, "openai": 0.0, "groq": 0.0}
_calls = {"gemini": [], "openai": [], "groq": []}
_last_call = threading.local()


def _cfg():
    return settings


def _clock() -> float:
    return time.monotonic()


def reset_state() -> None:
    """Reset provider counters and cooldowns. Primarily useful for tests."""
    with _lock:
        for provider in _cooldowns:
            _cooldowns[provider] = 0.0
            _calls[provider].clear()

    _last_call.model = None


def _primary_configured(cfg) -> bool:
    return (
        getattr(cfg, "llm_provider", "") in ("gemini", "openai")
        and bool(getattr(cfg, "llm_api_key", ""))
    )


def _groq_configured(cfg) -> bool:
    return bool(getattr(cfg, "groq_api_key", ""))


def is_configured() -> bool:
    cfg = _cfg()
    return _primary_configured(cfg) or _groq_configured(cfg)


def _model_for(provider: str, cfg) -> str:
    if provider == "groq":
        return (
            getattr(cfg, "groq_model", "")
            or DEFAULT_MODELS["groq"]
        )

    return (
        getattr(cfg, "llm_model", "")
        or DEFAULT_MODELS.get(provider, "")
    )


def model_name() -> str:
    """Return the model used for the most recent successful call in this thread."""
    cfg = _cfg()

    previous = getattr(_last_call, "model", None)
    if previous:
        return previous

    if _primary_configured(cfg):
        return _model_for(cfg.llm_provider, cfg)

    if _groq_configured(cfg):
        return _model_for("groq", cfg)

    return ""


def _reserve_call(provider: str, cfg) -> None:
    """Check this provider's cooldown and hourly limit."""
    with _lock:
        now = _clock()

        if now < _cooldowns[provider]:
            remaining = max(1, int(_cooldowns[provider] - now))
            raise LLMUnavailable(
                f"{provider} cooling down for {remaining}s"
            )

        _calls[provider][:] = [
            timestamp
            for timestamp in _calls[provider]
            if now - timestamp < 3600
        ]

        if len(_calls[provider]) >= cfg.llm_max_calls_per_hour:
            raise LLMUnavailable(
                f"{provider} hourly request limit reached"
            )

        _calls[provider].append(now)


def _parse_json(text: str) -> dict:
    cleaned = re.sub(
        r"^```(?:json)?\s*|\s*```$",
        "",
        (text or "").strip(),
    )

    try:
        value = json.loads(cleaned)
    except ValueError as error:
        raise LLMError("Model did not return valid JSON") from error

    if not isinstance(value, dict):
        raise LLMError("Model JSON was not an object")

    return value


def _retry_after_seconds(value: str | None) -> float | None:
    if not value:
        return None

    try:
        return max(0.0, float(value))
    except (ValueError, TypeError):
        pass

    try:
        retry_date = parsedate_to_datetime(value)

        if retry_date.tzinfo is None:
            retry_date = retry_date.replace(tzinfo=timezone.utc)

        return max(
            0.0,
            (retry_date - datetime.now(timezone.utc)).total_seconds(),
        )
    except (TypeError, ValueError, OverflowError):
        return None


def _raise_for_status(response, provider: str) -> None:
    if response.status_code >= 400:
        headers = getattr(response, "headers", {}) or {}

        raise LLMHTTPError(
            provider,
            response.status_code,
            _retry_after_seconds(headers.get("Retry-After")),
        )


def _call_gemini(cfg, system: str, user: str) -> str:
    response = requests.post(
        GEMINI_URL.format(model=_model_for("gemini", cfg)),
        headers={
            "x-goog-api-key": cfg.llm_api_key,
            "Content-Type": "application/json",
        },
        json={
            "systemInstruction": {
                "parts": [{"text": system}]
            },
            "contents": [
                {
                    "role": "user",
                    "parts": [{"text": user}],
                }
            ],
            "generationConfig": {
                "responseMimeType": "application/json",
            },
        },
        timeout=cfg.llm_timeout,
    )

    _raise_for_status(response, "Gemini")

    try:
        return response.json()["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise LLMError("Unexpected Gemini response shape") from error


def _call_openai(cfg, system: str, user: str) -> str:
    response = requests.post(
        OPENAI_URL,
        headers={
            "Authorization": f"Bearer {cfg.llm_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": _model_for("openai", cfg),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0.1,
        },
        timeout=cfg.llm_timeout,
    )

    _raise_for_status(response, "OpenAI")

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise LLMError("Unexpected OpenAI response shape") from error


def _call_groq(cfg, system: str, user: str) -> str:
    response = requests.post(
        GROQ_URL,
        headers={
            "Authorization": f"Bearer {cfg.groq_api_key}",
            "Content-Type": "application/json",
        },
        json={
            "model": _model_for("groq", cfg),
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {"type": "json_object"},
        },
        timeout=cfg.llm_timeout,
    )

    _raise_for_status(response, "Groq")

    try:
        return response.json()["choices"][0]["message"]["content"]
    except (KeyError, IndexError, TypeError, ValueError) as error:
        raise LLMError("Unexpected Groq response shape") from error


def _retry_delay(attempt: int, error: Exception) -> float:
    if isinstance(error, LLMHTTPError) and error.retry_after is not None:
        return min(error.retry_after, MAX_RETRY_DELAY)

    return min(
        BASE_RETRY_DELAY * (2 ** (attempt - 1)),
        MAX_RETRY_DELAY,
    )


def _is_retryable(error: Exception) -> bool:
    if isinstance(error, LLMHTTPError):
        return error.status_code in RETRYABLE_STATUS_CODES

    return False


def _fail(provider: str, cfg, error: Exception) -> None:
    with _lock:
        _cooldowns[provider] = (
            _clock() + cfg.llm_cooldown_seconds
        )

    logger.warning(
        "%s call failed (%s). Cooling down for %ss.",
        provider,
        error,
        cfg.llm_cooldown_seconds,
    )


def _attempt_provider(provider: str, cfg, system: str, user: str) -> dict:
    """Try one provider, including its bounded retries and JSON validation."""

    call_function = {
        "gemini": _call_gemini,
        "openai": _call_openai,
        "groq": _call_groq,
    }[provider]

    for attempt in range(1, MAX_ATTEMPTS + 1):
        try:
            _reserve_call(provider, cfg)

            response_text = call_function(cfg, system, user)
            result = _parse_json(response_text)

            _last_call.model = _model_for(provider, cfg)
            return result

        except LLMUnavailable:
            raise

        except (LLMError, requests.RequestException) as error:
            retryable = _is_retryable(error)
            final_attempt = attempt == MAX_ATTEMPTS

            if retryable and not final_attempt:
                delay = _retry_delay(attempt, error)

                if (
                    isinstance(error, LLMHTTPError)
                    and error.retry_after is not None
                    and error.retry_after > MAX_RETRY_DELAY
                ):
                    _fail(provider, cfg, error)
                    raise LLMError(
                        f"{error}. Retry-After exceeds the retry limit"
                    ) from error

                logger.warning(
                    "Temporary %s failure on attempt %s/%s. "
                    "Retrying in %.1fs.",
                    provider,
                    attempt,
                    MAX_ATTEMPTS,
                    delay,
                )

                time.sleep(delay)
                continue

            _fail(provider, cfg, error)

            if isinstance(error, LLMError):
                raise

            raise LLMError(
                f"{type(error).__name__} calling {provider}"
            ) from error

    raise LLMError(f"{provider} request failed after all attempts")


def complete_json(system: str, user: str) -> dict:
    """
    Try the configured primary provider first, then Groq if available.

    Every provider has its own hourly limit and cooldown.
    Never returns unvalidated model text.
    """
    cfg = _cfg()

    primary = (
        cfg.llm_provider
        if _primary_configured(cfg)
        else None
    )
    groq_available = _groq_configured(cfg)

    if primary is None and not groq_available:
        raise LLMUnavailable("No LLM provider configured")

    primary_error = None

    if primary is not None:
        try:
            return _attempt_provider(primary, cfg, system, user)
        except (LLMError, requests.RequestException) as error:
            primary_error = error

            if not groq_available:
                raise

            logger.warning(
                "%s unavailable. Trying Groq fallback.",
                primary,
            )

    if groq_available:
        try:
            return _attempt_provider("groq", cfg, system, user)
        except (LLMError, requests.RequestException):
            if primary_error is not None:
                raise primary_error
            raise

    if primary_error is not None:
        raise primary_error

    raise LLMUnavailable("No LLM provider available")
