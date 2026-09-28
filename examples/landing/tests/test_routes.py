"""Route smoke tests — all 8 B2 routes return 200 with HTML.

# req: REQ-P2-B2-001, REQ-P2-B2-005
"""
from __future__ import annotations

import pytest


@pytest.mark.parametrize(
    "path",
    [
        "/",
        "/features",
        "/adapter-matrix",
        "/demo",
        "/performance",
        "/security",
        "/docs",
        "/install",
    ],
)
def test_route_returns_200(client, path: str) -> None:
    """All 8 B2 routes return 200 with text/html."""
    response = client.get(path)
    assert response.status_code == 200, f"{path} returned {response.status_code}"
    assert "text/html" in response.headers["content-type"]


def test_unknown_route_returns_404(client) -> None:
    """Unknown paths return 404."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
