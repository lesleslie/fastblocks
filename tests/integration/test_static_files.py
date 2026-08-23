"""Static files integration test (2 scenarios per Erratum 7).

Per Erratum 7: v3.1's scenario 1 (Cache-Control: public, max-age=31536000,
immutable) was DROPPED because Starlette's default StaticFiles has no
Cache-Control handling AND fastblocks' CacheControlMiddleware is defined
but never registered. Asserting Cache-Control would fail without a
production-code change (strict-tests-only violation).

Per Task 11 lesson-learned: brief assumptions substituted — bare
``FastBlocksApp()`` ships with an empty router (no static mount). The
production routes adapter (which would mount ``/static`` on ``/tmp/static``)
is only wired by the full ``App`` class, not by ``FastBlocksApp`` alone.
The fixture here attaches a Starlette ``Mount(/static, StaticFiles(...))``
pointing at a per-test directory so the integration test exercises real
static-file behavior end-to-end. The brotli scenario also installs
``BrotliMiddleware`` (``brotli_asgi`` -- the same library fastblocks'
own middleware stack uses at ``fastblocks/middleware.py:39``) so the
compression assertion actually fires; bare ``StaticFiles`` does no
compression.
"""

from __future__ import annotations

from pathlib import Path

import pytest
from brotli_asgi import BrotliMiddleware
from starlette.routing import Mount
from starlette.staticfiles import StaticFiles
from starlette.testclient import TestClient


@pytest.fixture
def static_app(fastblocks_test_app, tmp_path: Path):
    """Per-test FastBlocksApp with /static mounted on a tmp_path directory.

    The bare ``fastblocks_test_app`` fixture ships with an empty router
    (no static mount). We attach a Starlette ``Mount`` so the test exercises
    real static-file serving without touching production code. We also
    add ``BrotliMiddleware`` so the compression scenario can observe
    ``content-encoding: br`` on the response.
    """
    static_dir = tmp_path / "static"
    static_dir.mkdir()
    # CSS body is intentionally >400 bytes so BrotliMiddleware's default
    # ``minimum_size`` (brotli_asgi default = 400) does not skip compression.
    css = (
        "/* fastblocks ui.css — long enough for BrotliMiddleware to compress */\n"
        "body { color: red; }\n"
        + ("a { color: blue; }\n" * 30)
    )
    (static_dir / "ui.css").write_text(css)
    fastblocks_test_app.add_middleware(BrotliMiddleware)
    fastblocks_test_app.router.routes.append(
        Mount("/static", app=StaticFiles(directory=str(static_dir)), name="static"),
    )
    return fastblocks_test_app


def test_static_ui_css_served(static_app) -> None:
    """Scenario 1: GET /static/ui.css → 200 with file contents.

    Per Erratum 7: only asserts the file is served; cache headers are
    deferred to a future phase that allows middleware registration changes.
    """
    client = TestClient(static_app)
    response = client.get("/static/ui.css")
    assert response.status_code == 200
    assert response.headers.get("content-type", "").startswith("text/css")


def test_static_brotli_compression(static_app) -> None:
    """Scenario 2: GET /static/ui.css with Accept-Encoding: br → brotli compressed."""
    client = TestClient(static_app)
    response = client.get("/static/ui.css", headers={"Accept-Encoding": "br"})
    assert response.status_code == 200
    assert response.headers.get("content-encoding") == "br"
