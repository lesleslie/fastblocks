"""D4: OOB swaps — the framework preserves OOB markup unchanged through the response pipeline.

The framework ships no ``oob_swap()`` helper (OOB is markup-driven).
This test asserts the framework does NOT mangle OOB attributes when
content flows through the template + response layers.

Per Task 6 C2: ``Jinja2Adapter.render_string`` does NOT exist. The
default adapter (``Templates``) only exposes ``render_template`` /
``render_component``. Per brief constraint C, this test uses
``jinja2.Environment(autoescape=True).from_string(...).render(...)`` —
the same pattern autoescape regression tests use (D3 boot test,
D6 security baseline).

The OOB contract is preserved as long as the rendered output
contains the ``hx-swap-oob="true"`` or ``hx-swap-oob="outerHTML"``
attribute literally. The autoescape layer must NOT touch the
``hx-swap-oob`` attribute name (which is a plain identifier, not
HTML markup needing escaping) and must NOT escape the value
(``true`` / ``outerHTML`` are not HTML-significant).
"""
from __future__ import annotations

from jinja2 import Environment


def test_oob_attributes_preserved_through_template_render():
    """``hx-swap-oob="true"`` survives template rendering."""
    env = Environment(autoescape=True)
    rendered = env.from_string(
        '<div hx-swap-oob="true">content</div>',
    ).render()
    assert 'hx-swap-oob="true"' in rendered, (
        f"D4: OOB attribute mangled by template rendering "
        f"(rendered={rendered!r})"
    )


def test_oob_with_outerhtml_swap_directive_preserved():
    """``hx-swap-oob="outerHTML"`` survives template rendering."""
    env = Environment(autoescape=True)
    rendered = env.from_string(
        '<div hx-swap-oob="outerHTML">replacement</div>',
    ).render()
    assert 'hx-swap-oob="outerHTML"' in rendered, (
        f"D4: OOB outerHTML attribute mangled by template rendering "
        f"(rendered={rendered!r})"
    )
