"""Jinja2 SSTI regression — asserts no autoescape bypass.

4 scenarios per master plan line 474:
1. {{ x }} — autoescape applies
2. [[ x ]] — fragment delimiter respects autoescape
3. {{ x | safe }} — | safe filter is honored (raw output, not a bypass)
4. Markup(adversarial) round-trip — Markup is Jinja2 safe-string type

Brief adaptation notes:
- ``init_envs`` is an async instance method on ``fastblocks.Templates``,
  not a module-level function (same finding as Task 4/5). The working
  equivalent for synchronous test-time Jinja2 rendering is
  ``jinja2.Environment(autoescape=True)`` which has the same escape
  contract as ``starlette_async_jinja`` (autoescape=True by default;
  verified in ``starlette_async_jinja/responses.py:108``).
- Scenario 2's ``[[ x ]]`` uses the fragment delimiters configured in
  ``TemplatesSettings.delimiters`` (``variable_start_string="[["``,
  ``variable_end_string="]]"``); the test passes them explicitly so it
  runs without depending on the production settings object.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest


@pytest.fixture
def ssti_payloads() -> dict[str, list[str]]:
    """Load SSTI payloads from tests/xss/ssti_payloads.json."""
    path = Path(__file__).parent.parent / "xss" / "ssti_payloads.json"
    return json.loads(path.read_text())


def _make_env() -> "Environment":  # noqa: F821 — jinja2.Environment
    """Build a Jinja2 environment matching FastBlocks' autoescape + delimiter contract.

    Fragment delimiters ``[[ ]]`` match ``TemplatesSettings.delimiters``.
    Autoescape mirrors ``starlette_async_jinja`` default (autoescape=True).
    """
    from jinja2 import Environment

    return Environment(
        autoescape=True,
        variable_start_string="[[",
        variable_end_string="]]",
        block_start_string="[%",
        block_end_string="%]",
        comment_start_string="[#",
        comment_end_string="#]",
    )


def test_autoescape_applies_to_double_brace(ssti_payloads) -> None:
    """Scenario 1: {{ x }} autoescapes."""
    from jinja2 import Environment

    env = Environment(autoescape=True)
    # Drop the metadata key — its value is a str (the _comment), not a list.
    all_payloads = sum(
        (v for k, v in ssti_payloads.items() if not k.startswith("_")),
        [],
    )
    for payload in all_payloads:
        rendered = env.from_string("{{ x }}").render(x=payload)
        # Autoescape converts < and > to &lt; and &gt;
        assert "&lt;" in rendered or "<" not in payload


def test_fragment_delimiter_respects_autoescape(ssti_payloads) -> None:
    """Scenario 2: [[ x ]] fragment delimiter respects autoescape."""
    env = _make_env()
    payload = "<script>alert(1)</script>"
    rendered = env.from_string("[[ x ]]").render(x=payload)
    assert "<script>" not in rendered


def test_safe_filter_honored(ssti_payloads) -> None:
    """Scenario 3: {{ x | safe }} — | safe filter is honored (raw output)."""
    from jinja2 import Environment

    # Scenario 3 uses default double-brace delimiters, not the fragment
    # delimiter — assert the canonical Jinja2 escape path, which is what
    # ``{{ x | safe }}`` exercises in production templates.
    env = Environment(autoescape=True)
    payload = "<script>alert(1)</script>"
    rendered = env.from_string("{{ x | safe }}").render(x=payload)
    # | safe disables autoescape; raw payload is in output (intentional)
    assert "<script>" in rendered


def test_markup_round_trip() -> None:
    """Scenario 4: Markup round-trip — Jinja2 safe-string type."""
    from markupsafe import Markup

    payload = "<b>hello</b>"
    safe = Markup(payload)
    assert str(safe) == payload
    assert isinstance(safe, Markup)
