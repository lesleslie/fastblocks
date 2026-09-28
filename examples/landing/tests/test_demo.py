"""Demo route tests — search-as-you-type interaction.

# req: REQ-P2-B2-001, REQ-P2-B2-005
"""
from __future__ import annotations


def test_demo_full_page_no_hx_header(client) -> None:
    """Normal GET renders the full page with the form, not a fragment."""
    response = client.get("/demo")
    body = response.text
    assert "<!DOCTYPE html>" in body
    assert 'hx-get="/demo"' in body


def test_demo_hx_request_returns_fragment(client) -> None:
    """HX-Request header triggers the partials/results.html fragment."""
    response = client.get("/demo?q=fast", headers={"HX-Request": "true"})
    assert response.status_code == 200
    body = response.text
    # The fragment should not include the full document wrapper.
    assert "<!DOCTYPE html>" not in body
    # The fake search contains 'fastblocks' which matches q='fast'.
    assert "fastblocks" in body


def test_demo_hx_request_no_results(client) -> None:
    """No matches yields the 'No matches.' fallback."""
    response = client.get("/demo?q=zzz", headers={"HX-Request": "true"})
    body = response.text
    assert "No matches." in body
