"""Jinja2 render mode tests.

# req: REQ-P2-B3-001
"""
from __future__ import annotations

import re


def test_jinja_render_returns_200(client) -> None:
    """"?render=jinja" returns 200 with the greeting card rendered via the Jinja2 macro."""
    response = client.get("/?render=jinja")
    assert response.status_code == 200
    body = response.text
    assert "greeting-card" in body
    assert "Ada Lovelace" in body
    assert "First programmer." in body


def test_jinja_render_includes_follow_button(client) -> None:
    """The Jinja2 macro emits a <button> containing the Follow label."""
    response = client.get("/?render=jinja")
    assert response.status_code == 200
    assert re.search(r"<button[^>]*>\s*Follow\s*</button>", response.text) is not None