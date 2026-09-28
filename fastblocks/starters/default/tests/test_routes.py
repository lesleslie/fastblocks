"""Route smoke tests — both routes return 200 with HTML.

# req: REQ-P2-B1-001, REQ-P2-B1-005
"""
from __future__ import annotations


def test_home_route_returns_html(client) -> None:
    """GET / returns 200 with text/html content."""
    response = client.get("/")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_demo_route_returns_html(client) -> None:
    """GET /demo returns 200 with text/html content."""
    response = client.get("/demo")
    assert response.status_code == 200
    assert "text/html" in response.headers["content-type"]


def test_unknown_route_returns_404(client) -> None:
    """Unknown paths return 404."""
    response = client.get("/does-not-exist")
    assert response.status_code == 404
