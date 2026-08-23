"""CSRF + HTMX integration test (3 scenarios per Erratum 6).

Per Erratum 6: v3.1's scenario 3 (form-field fallback) was DROPPED because
the production middleware does not promote form fields to headers. The
middleware copy logic does not exist in starlette_csrf or fastblocks/middleware.py.

Note on brief substitutions:

The brief's `/some-htmx-endpoint` and hard-coded `"valid-token"` /
`"expired-token"` strings are cargo-culted — no such route exists on the
bare ``fastblocks_test_app`` fixture, and starlette_csrf's CSRFMiddleware
does not have a notion of "expired" tokens (it validates that the cookie
and header BOTH deserialize to the same value via URLSafeSerializer;
arbitrary strings are not valid signed tokens).

Substitutions applied (matching the brief's INTENT — 3 CSRF scenarios):

* **Route**: registered a POST /some-htmx-endpoint that returns 200.
  Starlette returns 404 for any unregistered path; the brief's implicit
  assumption that the route already exists is wrong.
* **Middleware**: bare ``FastBlocksApp()`` does not install CSRF —
  ``MiddlewareStackManager._register_conditional_middleware`` early-
  returns when ``config is None`` (and the fixture's resolver has no
  config registered). We add ``CSRFMiddleware`` directly via
  ``app.add_middleware(...)`` with a known secret so the integration
  test exercises real CSRF behavior.
* **Scenarios**:
  - S1: POST with no cookies/headers → 403 (cookie-less request always
    rejected — matches "no token → 403").
  - S2: GET to mint the CSRF cookie, then POST with that cookie value
    as the X-CSRF-Token header → 200 (matches "valid header → 200").
  - S3: POST with the CSRF cookie but a garbage X-CSRF-Token header →
    403 (matches "expired token → 403"; replaced "expired" with the
    actual behavior — token mismatch).
"""

from __future__ import annotations

from starlette.responses import PlainTextResponse
from starlette.routing import Route
from starlette.testclient import TestClient
from starlette_csrf.middleware import CSRFMiddleware


# A long, fixed secret so signed tokens are deterministic across test runs.
# starlette_csrf wraps the cookie+header through URLSafeSerializer with
# this secret; replaying the same secret lets the test mint tokens.
_TEST_SECRET = "phase-5-v4-csrf-integration-secret" * 2  # 32+ chars
_COOKIE_NAME = "_fb__csrf"
# starlette_csrf defaults to header_name="x-csrftoken" (no hyphen), but
# the brief uses "X-CSRF-Token" with a hyphen. Configure the middleware
# to match so the brief's header name round-trips correctly.
_HEADER_NAME = "x-csrf-token"


def _htmx_endpoint(request):  # noqa: ANN001
    """Minimal HTMX-style endpoint that always returns 200."""
    return PlainTextResponse("ok", status_code=200)


def _build_test_app(fastblocks_test_app):
    """Attach CSRF + a test route to the bare FastBlocksApp fixture.

    Bare ``FastBlocksApp()`` does NOT install CSRFMiddleware (no config
    resolved in the fixture's resolver-clean state). We add the
    middleware directly via Starlette's ``add_middleware`` so the test
    exercises real CSRF behavior end-to-end.
    """
    fastblocks_test_app.add_middleware(
        CSRFMiddleware,
        secret=_TEST_SECRET,
        cookie_name=_COOKIE_NAME,
        header_name=_HEADER_NAME,
    )
    fastblocks_test_app.router.routes.append(
        Route("/some-htmx-endpoint", _htmx_endpoint, methods=["POST"]),
    )
    return fastblocks_test_app


def test_csrf_missing_token_returns_403(fastblocks_test_app) -> None:
    """Scenario 1: HTMX POST without CSRF token (no cookie, no header) → 403.

    The bare POST request has no CSRF cookie (set by the middleware on
    a prior response), so the middleware returns 403 before the route
    is reached.
    """
    app = _build_test_app(fastblocks_test_app)
    client = TestClient(app)

    response = client.post("/some-htmx-endpoint", headers={"HX-Request": "true"})

    assert response.status_code == 403, (
        f"Expected 403 for cookie-less POST; got {response.status_code} "
        f"with body={response.text!r}"
    )


def test_csrf_valid_header_returns_200(fastblocks_test_app) -> None:
    """Scenario 2: HTMX POST with matching CSRF cookie + signed X-CSRF-Token → 200.

    The ``fastblocks_test_app`` fixture does not install CSRF middleware
    by default (no config resolved), so we attach it explicitly. To make
    a request pass CSRF, the middleware requires (a) the request to carry
    the CSRF cookie set by a prior response AND (b) the X-CSRF-Token
    header to deserialize to the same inner value via the configured
    URLSafeSerializer secret. This test mints the cookie via an initial
    GET, captures it, then submits the captured value as both cookie and
    header on the POST.
    """
    app = _build_test_app(fastblocks_test_app)
    client = TestClient(app)

    # Prime: GET sets the CSRF cookie on the client.
    prime = client.get("/some-htmx-endpoint")
    assert prime.status_code in (200, 405)  # 405 if GET not allowed; cookie still set by middleware
    assert _COOKIE_NAME in client.cookies, (
        f"CSRF cookie {_COOKIE_NAME!r} not set on GET — middleware "
        f"should populate it for the next request"
    )
    signed_token = client.cookies[_COOKIE_NAME]

    response = client.post(
        "/some-htmx-endpoint",
        headers={"HX-Request": "true", "X-CSRF-Token": signed_token},
    )

    assert response.status_code == 200, (
        f"Expected 200 for matching cookie+header; got {response.status_code} "
        f"with body={response.text!r}"
    )


def test_csrf_expired_token_returns_403(fastblocks_test_app) -> None:
    """Scenario 3: HTMX POST with CSRF cookie + mismatched X-CSRF-Token → 403.

    starlette_csrf's CSRFMiddleware does not have an "expiry" concept —
    it validates that the cookie and header deserialize to the same
    inner value via URLSafeSerializer. We approximate the brief's
    "expired" semantics with a token that fails to match: the client
    sends the CSRF cookie (set by a GET) but a bogus header value. The
    middleware rejects on token mismatch → 403.
    """
    app = _build_test_app(fastblocks_test_app)
    client = TestClient(app)

    # Prime the cookie.
    prime = client.get("/some-htmx-endpoint")
    assert prime.status_code in (200, 405)
    assert _COOKIE_NAME in client.cookies

    # Submit a garbage header — middleware will reject via token-mismatch.
    response = client.post(
        "/some-htmx-endpoint",
        headers={"HX-Request": "true", "X-CSRF-Token": "expired-token"},
    )

    assert response.status_code == 403, (
        f"Expected 403 for cookie+garbage-header; got {response.status_code} "
        f"with body={response.text!r}"
    )
