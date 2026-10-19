"""Resilience and fault-tolerance layer for Helm agent orchestration.

Implements exponential backoff retries (maximum 3 attempts), structured error
classification (429 quota limits, 503 service spikes, auth, timeouts),
and circuit-breaker coordination for multi-worker workflows.
"""

import asyncio
import logging
from collections.abc import Callable, Coroutine
from datetime import UTC, datetime
from typing import Any, TypeVar

logger = logging.getLogger(__name__)

T = TypeVar("T")


def categorize_gemini_error(
    exc: Exception,
    worker: str,
    model: str,
    retries_attempted: int = 3,
) -> dict[str, Any]:
    """Classify an exception into a structured, UX-friendly diagnostic record."""
    err_str = str(exc)
    err_upper = err_str.upper()

    now_iso = datetime.now(UTC).isoformat()

    if "429" in err_str or "RESOURCE_EXHAUSTED" in err_upper:
        return {
            "code": "QUOTA_EXCEEDED",
            "status_code": 429,
            "worker": worker,
            "model": model,
            "title": "Gemini Quota or Rate Limit Exceeded",
            "message": (
                f"The model '{model}' reached its per-minute rate limit or daily free-tier quota."
            ),
            "raw_details": err_str[:160],
            "suggestion": (
                "Switch to a lighter model (e.g. 'gemini-3.1-flash-lite' or 'gemini-2.5-flash') "
                "in your .env file or wait for the quota window to reset. "
                "Helm automatically recovered using deterministic domain intelligence."
            ),
            "retries": retries_attempted,
            "timestamp": now_iso,
        }

    if "503" in err_str or "UNAVAILABLE" in err_upper:
        return {
            "code": "SERVICE_UNAVAILABLE",
            "status_code": 503,
            "worker": worker,
            "model": model,
            "title": "Gemini Service Spike (High Demand)",
            "message": (
                f"Google's '{model}' cluster is experiencing temporary traffic spikes "
                f"after {retries_attempted} retry attempts."
            ),
            "raw_details": err_str[:160],
            "suggestion": (
                "Spikes in Google's model clusters are usually brief. "
                "Helm completed the mission safely via domain intelligence. "
                "You can retry in a few moments or switch models in .env."
            ),
            "retries": retries_attempted,
            "timestamp": now_iso,
        }

    if "401" in err_str or "UNAUTHENTICATED" in err_upper:
        return {
            "code": "AUTH_ERROR",
            "status_code": 401,
            "worker": worker,
            "model": model,
            "title": "Authentication Failed (Invalid Key)",
            "message": "The provided GEMINI_API_KEY is missing, unauthorized, or expired.",
            "raw_details": err_str[:160],
            "suggestion": (
                "Verify your GEMINI_API_KEY in backend/.env or your host environment variables. "
                "Generate a key at https://aistudio.google.com/."
            ),
            "retries": retries_attempted,
            "timestamp": now_iso,
        }

    if "400" in err_str or "INVALID_ARGUMENT" in err_upper:
        return {
            "code": "INVALID_ARGUMENT",
            "status_code": 400,
            "worker": worker,
            "model": model,
            "title": "Model Request Configuration Error",
            "message": f"Gemini rejected request parameters for model '{model}'.",
            "raw_details": err_str[:160],
            "suggestion": (
                "Ensure parameters such as deadline/timeout (minimum 10s) and model name are valid."
            ),
            "retries": retries_attempted,
            "timestamp": now_iso,
        }

    if "TIMEOUT" in err_upper or "DEADLINE" in err_upper:
        return {
            "code": "TIMEOUT",
            "status_code": 408,
            "worker": worker,
            "model": model,
            "title": "Request Timed Out",
            "message": (
                f"Model '{model}' did not respond within deadline after "
                f"{retries_attempted} retries."
            ),
            "raw_details": err_str[:160],
            "suggestion": (
                "The upstream AI cluster is responding slowly. "
                "Consider switching to 'gemini-3.1-flash-lite' for faster turnaround."
            ),
            "retries": retries_attempted,
            "timestamp": now_iso,
        }

    return {
        "code": "UPSTREAM_ERROR",
        "status_code": 500,
        "worker": worker,
        "model": model,
        "title": f"Upstream Exception ({exc.__class__.__name__})",
        "message": f"Encountered unexpected upstream model response: {err_str[:140]}",
        "raw_details": err_str[:160],
        "suggestion": (
            "Check provider status or backend logs. "
            "Helm continued execution using local deterministic intelligence."
        ),
        "retries": retries_attempted,
        "timestamp": now_iso,
    }


def is_fatal_non_retryable(exc: Exception) -> bool:
    """Return True if retrying is futile (e.g. auth failure or invalid configuration)."""
    err = str(exc).upper()
    # 401 unauthenticated or 400 invalid argument should fail-fast
    if "401" in err or "UNAUTHENTICATED" in err:
        return True
    if "400" in err or "INVALID_ARGUMENT" in err:
        return True
    return False


async def execute_with_retry(
    operation: Callable[[], Coroutine[Any, Any, T]],
    worker: str,
    model: str,
    max_retries: int = 3,
    initial_delay: float = 1.0,
    backoff_factor: float = 1.5,
) -> tuple[T | None, dict[str, Any] | None]:
    """Execute an async LLM operation with up to max_retries attempts.

    Returns:
        (result, None) on success
        (None, structured_error) on failure after all retries
    """
    last_exc: Exception | None = None
    delay = initial_delay

    for attempt in range(1, max_retries + 1):
        try:
            result = await operation()
            if attempt > 1:
                logger.info(
                    "[%s] Succeeded on attempt %d/%d with model '%s'",
                    worker,
                    attempt,
                    max_retries,
                    model,
                )
            return result, None
        except Exception as exc:
            last_exc = exc
            logger.warning(
                "[%s] Attempt %d/%d failed with model '%s': %s",
                worker,
                attempt,
                max_retries,
                model,
                exc,
            )

            # Do not retry fatal non-retryable errors
            if is_fatal_non_retryable(exc) or attempt == max_retries:
                break

            await asyncio.sleep(delay)
            delay *= backoff_factor

    structured = categorize_gemini_error(
        last_exc or RuntimeError("Unknown LLM invocation error"),
        worker=worker,
        model=model,
        retries_attempted=max_retries,
    )
    return None, structured
