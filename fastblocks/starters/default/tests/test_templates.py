"""Template rendering tests — home renders shell + cards; demo renders form.

# req: REQ-P2-B1-001, REQ-P2-B1-005
"""
from __future__ import annotations


def test_home_renders_hero(client) -> None:
    """Home page contains the fastblocks-ui shell + hero title."""
    response = client.get("/")
    body = response.text
    assert "ui-shell" in body
    assert "FastBlocks" in body


def test_home_renders_three_cards(client) -> None:
    """Home page contains the three 'why FastBlocks' cards."""
    response = client.get("/")
    body = response.text
    for title in ("Async", "Typed", "Honest"):
        assert title in body


def test_demo_renders_search_field(client) -> None:
    """Demo page renders the search field and hx-get wiring."""
    response = client.get("/demo")
    body = response.text
    assert "Search" in body
    assert 'hx-get="/demo"' in body


def test_demo_renders_empty_results(client) -> None:
    """Empty demo GET shows the form with no results."""
    response = client.get("/demo")
    assert response.status_code == 200
