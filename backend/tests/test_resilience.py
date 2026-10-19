"""Unit tests for Helm resilience, 3-retry execution, and structured error categorization."""

import pytest

from app.core.resilience import (
    categorize_gemini_error,
    execute_with_retry,
    is_fatal_non_retryable,
)


def test_categorize_quota_exceeded():
    exc = Exception("429 RESOURCE_EXHAUSTED: Rate limit reached for model gemini-3.8-flash")
    diag = categorize_gemini_error(
        exc, worker="Researcher", model="gemini-3.8-flash", retries_attempted=3
    )
    assert diag["code"] == "QUOTA_EXCEEDED"
    assert diag["status_code"] == 429
    assert diag["worker"] == "Researcher"
    assert diag["retries"] == 3
    assert "quota" in diag["suggestion"].lower()


def test_categorize_service_unavailable():
    exc = Exception("503 UNAVAILABLE: The model is currently experiencing high demand.")
    diag = categorize_gemini_error(
        exc, worker="Supervisor Router", model="gemini-3.8-flash", retries_attempted=3
    )
    assert diag["code"] == "SERVICE_UNAVAILABLE"
    assert diag["status_code"] == 503
    assert diag["retries"] == 3


def test_categorize_auth_error_and_fail_fast():
    exc = Exception("401 UNAUTHENTICATED: Invalid API key provided.")
    diag = categorize_gemini_error(
        exc, worker="Coder", model="gemini-3.8-flash", retries_attempted=1
    )
    assert diag["code"] == "AUTH_ERROR"
    assert diag["status_code"] == 401
    assert is_fatal_non_retryable(exc) is True


@pytest.mark.asyncio
async def test_execute_with_retry_success():
    attempts = 0

    async def _operation():
        nonlocal attempts
        attempts += 1
        return "success"

    result, err = await execute_with_retry(
        _operation,
        worker="test-worker",
        model="test-model",
        max_retries=3,
        initial_delay=0.01,
    )
    assert result == "success"
    assert err is None
    assert attempts == 1


@pytest.mark.asyncio
async def test_execute_with_retry_transient_failure_then_success():
    attempts = 0

    async def _operation():
        nonlocal attempts
        attempts += 1
        if attempts < 3:
            raise Exception("503 UNAVAILABLE: High demand spike")
        return "recovered"

    result, err = await execute_with_retry(
        _operation,
        worker="test-worker",
        model="test-model",
        max_retries=3,
        initial_delay=0.01,
    )
    assert result == "recovered"
    assert err is None
    assert attempts == 3


@pytest.mark.asyncio
async def test_execute_with_retry_exhausted_retries():
    attempts = 0

    async def _operation():
        nonlocal attempts
        attempts += 1
        raise Exception("429 RESOURCE_EXHAUSTED: Daily quota exceeded")

    result, diag = await execute_with_retry(
        _operation,
        worker="test-worker",
        model="test-model",
        max_retries=3,
        initial_delay=0.01,
    )
    assert result is None
    assert diag is not None
    assert diag["code"] == "QUOTA_EXCEEDED"
    assert diag["retries"] == 3
    assert attempts == 3


@pytest.mark.asyncio
async def test_execute_with_retry_fail_fast_on_auth_error():
    attempts = 0

    async def _operation():
        nonlocal attempts
        attempts += 1
        raise Exception("401 UNAUTHENTICATED: Bad key")

    result, diag = await execute_with_retry(
        _operation,
        worker="test-worker",
        model="test-model",
        max_retries=3,
        initial_delay=0.01,
    )
    assert result is None
    assert diag is not None
    assert diag["code"] == "AUTH_ERROR"
    # Should fail fast after only 1 attempt
    assert attempts == 1
