"""Consolidated, parameterized security tests for input validation.

Covers XSS prevention, SQL injection detection, and path-traversal rejection
in the FastBlocks validation layer.  These tests are the canonical source of
truth for the payload sets; per-module tests that exercise the same patterns
are annotated with a TODO pointing here.

Upstream source files that contain duplicate coverage (annotated below):
  - tests/test_validation_integration.py  (TestSecurityFeatures,
    TestTemplateContextValidation, TestFormInputValidation, TestAPIValidation)
  - tests/adapters/templates/test_htmy_loader.py  (TestScaffoldPathContainment,
    TestScaffolderCreatePathContainment)

Note: tests/adapters/templates/test_htmy_loader.py path-traversal tests
exercise a *different* code path (the HTMY component scaffolder AST walker)
and have NOT been annotated as duplicates — they test complementary logic.
Only the generic input-validation payload checks overlap.

Lifecycle note
--------------
The async tests in this file use ``@pytest.mark.asyncio`` + ``async def``
to give each test explicit ownership of its event loop via ``pytest-asyncio``
(``asyncio_mode = "auto"`` in ``pyproject.toml``).  This avoids the implicit
``asyncio.get_event_loop()`` pattern which on Python 3.10+ emits
``DeprecationWarning: There is no current event loop`` and on 3.14+ will be
removed entirely.  The synchronous helper tests continue to use the
``_contains_*`` helpers directly.
"""

from __future__ import annotations

import asyncio

import pytest


# ---------------------------------------------------------------------------
# Payload lists (single source of truth)
# ---------------------------------------------------------------------------

XSS_PAYLOADS: list[str] = [
    "<script>alert(1)</script>",
    "javascript:alert(1)",
    "<img src=x onerror=alert(1)>",
    "<svg onload=alert(1)>",
    '"><script>alert(document.cookie)</script>',
    "<iframe src=javascript:alert(1)>",
    "<body onload=alert(1)>",
    "'-alert(1)-'",
    '";alert(1);//',
    "<script>alert('XSS')</script>",
]

SQLI_PAYLOADS: list[str] = [
    "' OR 1=1 --",
    "'; DROP TABLE users; --",
    "admin' OR '1'='1",
    "' UNION SELECT * FROM users --",
    "'; DELETE FROM users WHERE '1'='1",
    "admin'--",
    "' OR 'x'='x",
    "' OR 1=1#",
    "1=1",
    '" OR ""="',
]

PATH_TRAVERSAL_PAYLOADS: list[str] = [
    "../../../etc/passwd",
    "..\\..\\..\\windows\\system32",
    "%2e%2e%2f",
    "....//",
    "../../etc/shadow",
    "./../../../etc",
    "%252e%252e%252f",
    "..%2f..%2f..%2fetc%2fpasswd",
]

SAFE_INPUTS: list[str] = [
    "normal text",
    "user@example.com",
    "valid-username_123",
    "This is a normal sentence.",
    "hello world",
    "product-v2.0",
]


# ---------------------------------------------------------------------------
# Helpers to load the validation service (graceful skip when unavailable)
# ---------------------------------------------------------------------------


def _get_validation_service():
    """Return the validation service or skip the calling test."""
    try:
        from fastblocks._validation_integration import get_validation_service

        svc = get_validation_service()
    except ImportError:
        pytest.skip("Validation integration not available")
    return svc


# ---------------------------------------------------------------------------
# XSS prevention
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
async def test_xss_payload_not_in_sanitized_template_context(payload: str) -> None:
    """XSS payloads must be stripped / escaped in template context sanitization."""
    svc = _get_validation_service()
    if not (svc.available and svc._config.prevent_xss):
        pytest.skip("XSS prevention not active in this environment")

    _is_valid, sanitized, _errors = await svc.validate_template_context(
        context={"content": payload},
        template_name="test.html",
        strict=False,
    )
    assert "<script>" not in str(sanitized.get("content", "")), (
        f"XSS payload not sanitized in template context: {payload!r}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
async def test_xss_payload_not_in_sanitized_form_input(payload: str) -> None:
    """XSS payloads must be stripped / escaped in form input sanitization."""
    svc = _get_validation_service()
    if not (svc.available and svc._config.prevent_xss):
        pytest.skip("XSS prevention not active in this environment")

    _is_valid, sanitized, _errors = await svc.validate_form_input(
        form_data={"comment": payload},
        schema=None,
        strict=False,
    )
    assert "<script>" not in str(sanitized.get("comment", "")), (
        f"XSS payload not sanitized in form input: {payload!r}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", XSS_PAYLOADS)
async def test_xss_payload_not_in_sanitized_api_request(payload: str) -> None:
    """XSS payloads must be stripped / escaped in API request sanitization."""
    svc = _get_validation_service()
    if not (svc.available and svc._config.prevent_xss):
        pytest.skip("XSS prevention not active in this environment")

    _is_valid, validated, _errors = await svc.validate_api_request(
        request_data={"comment": payload},
        schema=None,
    )
    assert "<script>" not in str(validated.get("comment", "")), (
        f"XSS payload not sanitized in API request: {payload!r}"
    )


# ---------------------------------------------------------------------------
# SQL injection detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
def test_sqli_payload_detected_by_contains_helper(payload: str) -> None:
    """The low-level _contains_sql_injection helper must flag every payload."""
    svc = _get_validation_service()
    if not svc.available:
        pytest.skip("Validation service not available")

    assert svc._contains_sql_injection(payload), (
        f"SQL injection payload not detected: {payload!r}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
async def test_sqli_payload_generates_error_in_template_context(payload: str) -> None:
    """SQLi payloads in template context must produce at least one error entry."""
    svc = _get_validation_service()
    if not (svc.available and svc._config.prevent_sql_injection):
        pytest.skip("SQL injection prevention not active in this environment")

    _is_valid, _sanitized, errors = await svc.validate_template_context(
        context={"search": payload},
        template_name="test.html",
        strict=False,
    )
    assert any("SQL injection" in e for e in errors), (
        f"No SQL injection error raised for payload: {payload!r}; errors: {errors}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", SQLI_PAYLOADS)
async def test_sqli_payload_generates_error_in_form_input(payload: str) -> None:
    """SQLi payloads in form input must produce at least one error entry."""
    svc = _get_validation_service()
    if not (svc.available and svc._config.prevent_sql_injection):
        pytest.skip("SQL injection prevention not active in this environment")

    _is_valid, _sanitized, errors = await svc.validate_form_input(
        form_data={"search": payload},
        schema=None,
        strict=False,
    )
    assert any("SQL injection" in e for e in errors), (
        f"No SQL injection error raised for payload: {payload!r}; errors: {errors}"
    )


# ---------------------------------------------------------------------------
# Path-traversal detection
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
def test_path_traversal_detected_by_contains_helper(payload: str) -> None:
    """The low-level _contains_path_traversal helper must flag every payload."""
    svc = _get_validation_service()
    if not svc.available:
        pytest.skip("Validation service not available")

    assert svc._contains_path_traversal(payload), (
        f"Path traversal payload not detected: {payload!r}"
    )


@pytest.mark.unit
@pytest.mark.asyncio
@pytest.mark.parametrize("payload", PATH_TRAVERSAL_PAYLOADS)
async def test_path_traversal_generates_error_in_form_input(payload: str) -> None:
    """Path-traversal payloads in form input must produce at least one error entry."""
    svc = _get_validation_service()
    if not (svc.available and svc._config.prevent_path_traversal):
        pytest.skip("Path traversal prevention not active in this environment")

    _is_valid, _sanitized, errors = await svc.validate_form_input(
        form_data={"file_path": payload},
        schema=None,
        strict=False,
    )
    assert any("path traversal" in e for e in errors), (
        f"No path traversal error raised for payload: {payload!r}; errors: {errors}"
    )


# ---------------------------------------------------------------------------
# False-positive guard: safe inputs must not be flagged
# ---------------------------------------------------------------------------


@pytest.mark.unit
@pytest.mark.parametrize("safe_input", SAFE_INPUTS)
def test_safe_input_not_flagged_as_sql_injection(safe_input: str) -> None:
    """The SQL injection detector must not produce false positives on safe text."""
    svc = _get_validation_service()
    if not svc.available:
        pytest.skip("Validation service not available")

    assert not svc._contains_sql_injection(safe_input), (
        f"False positive — safe input flagged as SQL injection: {safe_input!r}"
    )


@pytest.mark.unit
@pytest.mark.parametrize("safe_input", SAFE_INPUTS)
def test_safe_input_not_flagged_as_path_traversal(safe_input: str) -> None:
    """The path-traversal detector must not produce false positives on safe text."""
    svc = _get_validation_service()
    if not svc.available:
        pytest.skip("Validation service not available")

    assert not svc._contains_path_traversal(safe_input), (
        f"False positive — safe input flagged as path traversal: {safe_input!r}"
    )


# ---------------------------------------------------------------------------
# Lifecycle regression: explicit async runner
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_path_traversal_rejected_via_explicit_asyncio_run() -> None:
    """Regression: path-traversal form input must be rejected when the validation
    coroutine is driven through an explicitly created event loop (``asyncio.run``).

    This test guards against a class of failures where a sync test helper calls
    ``asyncio.get_event_loop().run_until_complete(...)`` on a thread that has
    no running loop.  On Python 3.10+ that pattern emits
    ``DeprecationWarning: There is no current event loop``; on 3.14+ it is
    removed entirely.  Using ``asyncio.run`` here proves that the validation
    coroutine itself does not depend on main-thread loop state — only the
    caller does — so converting the suite to ``async def`` (or to
    ``asyncio.run`` wrappers) is a pure mechanical fix.

    Asserts the same payload and rejection condition as the parametrized
    ``test_path_traversal_generates_error_in_form_input`` cases.
    """
    payload = "../../../etc/passwd"

    svc = _get_validation_service()
    if not (svc.available and svc._config.prevent_path_traversal):
        pytest.skip("Path traversal prevention not active in this environment")

    async def _validate_form(value: str) -> tuple[bool, dict[str, str], list[str]]:
        return await svc.validate_form_input(
            form_data={"file_path": value},
            schema=None,
            strict=False,
        )

    _is_valid, _sanitized, errors = asyncio.run(_validate_form(payload))

    assert any("path traversal" in e for e in errors), (
        f"No path traversal error raised for payload: {payload!r}; "
        f"errors: {errors}"
    )
