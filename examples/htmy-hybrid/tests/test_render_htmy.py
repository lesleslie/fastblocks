"""HTMY render mode tests.

# req: REQ-P2-B3-001
"""
from __future__ import annotations

import re


def test_htmy_render_returns_200(client) -> None:
    """"?render=htmy" returns 200 with the GreetingCard rendered via the HTMY Renderer."""
    response = client.get("/?render=htmy")
    assert response.status_code == 200
    body = response.text
    assert "greeting-card" in body
    assert "Ada Lovelace" in body
    assert "First programmer." in body


def test_htmy_render_includes_follow_button(client) -> None:
    """The HTMY component emits a <button> containing the Follow label.

    HTMY normalises text children with surrounding whitespace, so the
    assertion tolerates whitespace around the inner text.
    """
    response = client.get("/?render=htmy")
    assert response.status_code == 200
    assert re.search(r"<button[^>]*>\s*Follow\s*</button>", response.text) is not None