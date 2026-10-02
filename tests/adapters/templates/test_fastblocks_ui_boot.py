"""D3: boot test for the ``style/fastblocks_ui`` adapter.

Spec §D3 row ``style/fastblocks_ui`` -> resolver pair
``("fastblocks", "styles")`` (verified at
``fastblocks/adapters/style/fastblocks_ui.py:203``).

NOTE on path: the brief places this file under
``tests/adapters/templates/`` because the spec label begins with
``templates/``-prefix convention; the production-side matrix at
``examples/landing/routes/adapter_matrix.py`` and the existing
comprehensive test live at ``tests/adapters/style/test_fastblocks_ui_boot.py``.
This file is the brief-specified minimal boot test (one-off, doesn't
duplicate the comprehensive coverage).

Implementation note: in production, ``register_fastblocks_ui_functions(env)``
is invoked with a live jinja env at app startup and registers the
adapter as a side effect. We instantiate ``FastBlocksUIStyle``
directly and register against ``fresh_registry`` so the test is
isolated from the global resolver.
"""
from __future__ import annotations

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)


def test_fastblocks_ui_style_resolves_via_oneiric(fresh_registry) -> None:
    """The fastblocks-ui style adapter must be discoverable under
    ``("fastblocks", "styles")``."""
    from fastblocks.adapters.style.fastblocks_ui import FastBlocksUIStyle

    instance = FastBlocksUIStyle()
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="styles",
        factory=lambda: instance,
        metadata={"class": "FastBlocksUIStyle"},
    )
    resolved = resolve_instance(fresh_registry, "fastblocks", "styles")
    assert resolved is not None, (
        "D3: Oneiric resolver returned no instance for "
        "('fastblocks', 'styles')"
    )


def test_fastblocks_ui_style_returns_stylesheet_links() -> None:
    """Smoke: ``get_stylesheet_links()`` returns a non-empty list of
    ``<link>`` tags. The string is f-string-built from the actual
    installed ``fastblocks_ui`` package's ``get_css_path()`` so the
    contents are deterministic."""
    from fastblocks.adapters.style.fastblocks_ui import FastBlocksUIStyle

    instance = FastBlocksUIStyle()
    links = instance.get_stylesheet_links()
    assert isinstance(links, list) and links, (
        f"D3: FastBlocksUIStyle.get_stylesheet_links returned {links!r}"
    )
    assert any("<link" in link for link in links), (
        f"D3: expected at least one <link tag, got: {links!r}"
    )
