"""D3: boot test for the fastblocks-ui style adapter.

Note: the Oneiric key is ``("fastblocks", "styles")`` (plural) — not
``("fastblocks", "style")``. Verified via the ``register_candidate``
call inside ``fastblocks/adapters/style/fastblocks_ui.py:register_fastblocks_ui_functions``.

Implementation note: in production, the style registration lives
inside ``register_fastblocks_ui_functions(env)`` — a helper function
that is never invoked at module-import time. To exercise the boot
wiring in isolation, we instantiate ``FastBlocksUIStyle`` directly
and register against ``fresh_registry`` (mirroring what the helper
would do at app startup).
"""
from __future__ import annotations

import pytest

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)


@pytest.fixture
def style_adapter(fresh_registry):
    from fastblocks.adapters.style.fastblocks_ui import FastBlocksUIStyle

    style = FastBlocksUIStyle()
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="styles",
        factory=lambda: style,
        metadata={"class": "FastBlocksUIStyle"},
    )
    return resolve_instance(fresh_registry, "fastblocks", "styles")


def test_style_adapter_resolves(style_adapter):
    assert style_adapter is not None


def test_style_adapter_exposes_stylesheet_link_method(style_adapter):
    """Contract: style adapter must expose stylesheet links (used by
    landing's <head> rendering). The exact method name varies per
    adapter; assert it exists and returns a non-empty list/str.
    """
    get_links = getattr(style_adapter, "get_stylesheet_links", None)
    if get_links is None:
        get_links = getattr(style_adapter, "stylesheet_links", None)
    assert get_links is not None, (
        f"D3: style adapter {type(style_adapter).__name__} "
        f"exposes no stylesheet-link accessor"
    )
    links = get_links() if callable(get_links) else get_links
    assert links, "D3: style adapter returned empty stylesheet links"
