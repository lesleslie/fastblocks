"""D6: state-changing routes require a CSRF token.

Per security-auditor BL2: previous test only covered the negative path
(missing token rejected). A positive path test catches "CSRF middleware
blocks everything" (DoS), "rejects valid tokens" (lockout), and
"applies to wrong verbs" regressions.

The brief's ``FastBlocks(enable_csrf=True)`` + ``/submit`` route sketch
was reality-adapted: there is no ``enable_csrf`` kwarg on
``FastBlocks`` — CSRF is registered by ``MiddlewareStackManager`` when
``config.app.secret_key`` is set. We follow the established pattern
from ``tests/integration/test_csrf_htmx.py``: build a minimal Starlette
app, attach ``CSRFMiddleware`` directly via ``add_middleware``, and
register a real POST route via ``router.routes.append``. The TestClient
then drives real HTTP requests through the middleware.
"""

from __future__ import annotations

import pytest
from starlette.applications import Starlette
from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette_csrf.middleware import CSRFMiddleware

# Per existing tests/integration/test_csrf_htmx.py: a long, fixed secret
# so signed tokens are deterministic across test runs. starlette_csrf
# wraps the cookie+header through URLSafeSerializer with this secret.
_TEST_SECRET = "phase-5-v4-csrf-integration-secret" * 2  # 32+ chars
_COOKIE_NAME = "_fb__csrf"
_HEADER_NAME = "x-csrf-token"


def _submit(request):  # noqa: ANN001
    """Minimal POST endpoint that always returns 200."""
    return PlainTextResponse("ok", status_code=200)


def _read(request):  # noqa: ANN001
    """Minimal GET endpoint that always returns 200."""
    return PlainTextResponse("ok", status_code=200)


def _make_submit_app():
    """Build a Starlette app with CSRFMiddleware + /submit + /read."""
    app = Starlette()
    app.add_middleware(
        CSRFMiddleware,
        secret=_TEST_SECRET,
        cookie_name=_COOKIE_NAME,
        header_name=_HEADER_NAME,
    )
    app.router.routes.append(Route("/submit", _submit, methods=["POST"]))
    app.router.routes.append(Route("/read", _read, methods=["GET"]))
    return app


def test_post_without_csrf_token_rejected():
    """Negative path: missing token must be rejected with 403."""
    app = _make_submit_app()
    client = TestClient(app)
    r = client.post("/submit", json={"data": "x"})
    assert r.status_code == 403, (
        f"D6: CSRF middleware did not reject POST without token "
        f"(status={r.status_code})"
    )


def test_get_request_exempt_from_csrf():
    """GET (idempotent) must not require a token — catches over-eager CSRF.

    Implementation note: starlette_csrf exempts "safe" verbs (GET/HEAD/
    OPTIONS) by default. This test pins that contract.
    """
    app = _make_submit_app()
    client = TestClient(app)
    r = client.get("/read")
    assert r.status_code == 200, (
        f"D6: GET should not require CSRF token (status={r.status_code})"
    )


def test_post_with_valid_csrf_token_succeeds():
    """Positive path: a valid token must be accepted.

    CSRF semantics (starlette_csrf): the middleware requires BOTH the
    CSRF cookie AND the X-CSRF-Token header to deserialize to the same
    inner value via URLSafeSerializer. We mint the cookie via an
    initial GET, capture the cookie value, then submit it as the
    X-CSRF-Token header on the POST.
    """
    app = _make_submit_app()
    client = TestClient(app)

    # Prime: GET sets the CSRF cookie on the client.
    prime = client.get("/read")
    assert prime.status_code == 200, (
        f"D6: priming GET failed: {prime.status_code} {prime.text!r}"
    )
    assert _COOKIE_NAME in client.cookies, (
        f"D6: CSRF cookie {_COOKIE_NAME!r} not set on GET — middleware "
        "should populate it for the next request"
    )
    signed_token = client.cookies[_COOKIE_NAME]

    response = client.post(
        "/submit",
        headers={"X-CSRF-Token": signed_token},
    )
    assert response.status_code == 200, (
        f"D6: valid CSRF token rejected (status={response.status_code} "
        f"body={response.text!r})"
    )


def test_post_with_mismatched_csrf_token_rejected():
    """Submitting the cookie but a garbage header must be rejected.

    starlette_csrf has no "expiry" concept — it validates that the
    cookie and header deserialize to the same inner value. A garbage
    header value fails the match and the middleware returns 403.
    """
    app = _make_submit_app()
    client = TestClient(app)

    # Prime the cookie.
    prime = client.get("/read")
    assert prime.status_code == 200
    assert _COOKIE_NAME in client.cookies

    response = client.post(
        "/submit",
        headers={"X-CSRF-Token": "definitely-not-the-signed-token"},
    )
    assert response.status_code == 403, (
        f"D6: mismatched CSRF token was not rejected "
        f"(status={response.status_code})"
    )


def test_csrf_token_bound_to_session():
    """Submitting a token issued in session A to session B must be rejected.

    Per the threat model: CSRF tokens must be session-bound. If the
    framework accepts a token issued in a different session, this is a
    regression. starlette_csrf's CSRFMiddleware uses URLSafeSerializer
    on a server-side secret — it is NOT session-bound by default (a
    signed cookie is sufficient on its own). This test documents the
    gap for Phase 1.5 follow-up; until the framework binds tokens to
    sessions, this assertion must be skipped.
    """
    pytest.skip(
        "Session-binding test depends on framework CSRF session support; "
        "starlette_csrf does not bind tokens to sessions by default. "
        "Phase 1.5 follow-up: introduce session-aware CSRF."
    )
