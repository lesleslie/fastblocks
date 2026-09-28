"""Hybrid (HTMY-in-Jinja2) render mode and snapshot-equivalence tests.

The semantic-equivalence check is the load-bearing test for B3: it strips
the per-mode render-mode HTML comment markers, then asserts that all
three render modes produced the same structural greeting-card markup
(greeting-card div, Ada Lovelace heading, First programmer. paragraph,
Follow button).

HTMY and Jinja2 emit differently-formatted HTML — HTMY adds trailing
whitespace inside self-closing tags (``<h2 >``), renders ``<img/>``
self-closing, and adds blank lines around text children. The test
normalises whitespace and tag attributes before comparing, so the
assertion is structural rather than byte-equality.

# req: REQ-P2-B3-002, REQ-P2-B3-003
"""
from __future__ import annotations

import re


def test_hybrid_render_returns_200(client) -> None:
    """"?render=hybrid" returns 200 with the greeting card embedded in a Jinja2 layout."""
    response = client.get("/?render=hybrid")
    assert response.status_code == 200
    body = response.text
    assert "greeting-card" in body
    assert "Ada Lovelace" in body
    assert "First programmer." in body
    assert "<button" in body


def test_all_three_modes_are_200(client) -> None:
    """All three render modes return 200 — the boot-test for the demo."""
    for mode in ("jinja", "htmy", "hybrid"):
        response = client.get(f"/?render={mode}")
        assert response.status_code == 200, f"?render={mode} returned {response.status_code}"


def test_all_three_modes_semantically_equivalent(client) -> None:
    """Snapshot-based semantic equivalence.

    Each render mode embeds an HTML comment marker
    (``<!--render:<mode>-->``) inside its body. Strip those markers, then
    check that the remaining DOM has the same greeting-card structure:
    a div with class ``greeting-card`` containing the expected name, bio,
    and Follow button.
    """
    responses = [client.get(f"/?render={mode}") for mode in ("jinja", "htmy", "hybrid")]
    bodies = [_strip_render_marker(r.text) for r in responses]

    for body in bodies:
        assert 'class="greeting-card"' in body, "missing greeting-card div"
        assert "Ada Lovelace" in body, "missing Ada Lovelace"
        assert "First programmer." in body, "missing bio paragraph"
        assert re.search(r"<button[^>]*>\s*Follow\s*</button>", body) is not None, (
            "missing follow button"
        )

    # Stronger check: every mode emits structurally the same greeting-card
    # subtree. Normalise whitespace + self-closing tags before comparing so
    # the assertion is structural rather than byte-equality.
    card_pattern = re.compile(
        r'<div class="greeting-card">.*?</div>', re.DOTALL,
    )
    cards = [card_pattern.search(body) for body in bodies]
    for card in cards:
        assert card is not None, "greeting-card div not found"
    assert cards[0] is not None
    canonical = _normalise(cards[0].group(0))
    for card in cards[1:]:
        assert card is not None
        normalised = _normalise(card.group(0))
        assert normalised == canonical, (
            f"render-mode divs diverged after normalisation:\n"
            f"  normalised: {normalised!r}\n"
            f"  canonical:  {canonical!r}"
        )


def _strip_render_marker(body: str) -> str:
    """Strip the per-mode render-marker HTML comment from a response body."""
    return re.sub(r"<!--render:(jinja|htmy|hybrid)-->", "", body)


def _normalise(html_fragment: str) -> str:
    """Normalise whitespace + void-tag self-closing for snapshot comparison."""
    # Strip whitespace adjacent to ``>`` and ``<`` so HTMY's "<h2 >" and
    # the no-trailing-space Jinja2 form "<h2>" compare equal.
    out = re.sub(r"\s+<", "<", html_fragment)
    out = re.sub(r">\s+", ">", out)
    # Collapse any remaining internal whitespace to a single space and
    # strip the leading/trailing whitespace.
    out = re.sub(r"\s+", " ", out).strip()
    # Drop the trailing slash on self-closing void tags so HTMY
    # ``<img ... />`` and Jinja2 ``<img ...>`` compare equal.
    out = re.sub(r'(<(?:img|br|hr|input)[^>]*?)\s*/>', r"\1>", out)
    # Strip a stray space-before-``>`` that HTMY injects when an open
    # tag has no attributes (``<h2 >``).
    out = re.sub(r"<(\w+) >", r"<\1>", out)
    return out
