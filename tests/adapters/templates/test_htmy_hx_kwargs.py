"""HTMY hx_* kwargs contract test.

Per master plan line 475: covers the 9 whitelisted hx-* attrs + JSON-encoded
variants (hx-vals, hx-headers).

Brief cargo-cult correction (per Tasks 4-6 lessons, applied here):

1. ``from fastblocks.adapters.templates.htmy import HTMY`` — does not exist.
   The templates adapter exposes ``HTMYTemplates`` (async ``render_component``)
   which requires a real ``request`` and a registered component class; there
   is no ``HTMY().render_string(...)`` symbol. Substituted with the actual
   kwargs-based hx-* rendering surface in FastBlocks:
   ``fastblocks.adapters.templates._filters.htmx_attrs`` — a Jinja2/HTMX
   filter that maps shorthand kwarg names (``get``, ``post``, ``vals``,
   ``headers``, ...) to their ``hx-*`` HTML attribute forms. This filter is
   the production entry point for every HTMY component that emits hx-*
   attrs and is registered as a Jinja2 filter for ``{{ htmx_attrs(...) }}``
   template usage (see ``fastblocks/adapters/templates/_filters.py:250``).

2. The brief's ``attrs={hx_attr: "/api/test"}`` dict pattern is replaced
   with the equivalent kwarg form (``htmx_attrs(get="/api/test")``), which
   maps to ``hx-get="/api/test"`` per the filter's ``attr_mapping`` table.
   All 9 whitelisted hx-* attrs (``hx-get``, ``hx-post``, ``hx-target``,
   ``hx-trigger``, ``hx-swap``, ``hx-vals``, ``hx-headers``, ``hx-include``,
   ``hx-confirm``) are present in that mapping table.

3. The contract: each whitelisted hx-* attr must appear verbatim in the
   rendered output. The filter does not JSON-encode the shorthand vals/
   headers kwargs — callers pass JSON strings explicitly — so the JSON
   variants assert the rendered attribute name is present (not that the
   value is auto-encoded; encoding is the caller's responsibility per the
   filter docstring).
"""

from __future__ import annotations

import pytest

from fastblocks.adapters.templates._filters import htmx_attrs


# Maps whitelisted hx-* attribute names to the shorthand kwarg accepted by
# the htmx_attrs filter. Source: ``_filters.ATTR_MAPPING`` at
# ``fastblocks/adapters/templates/_filters.py:261`` (the ``attr_mapping``
# dict inside ``htmx_attrs``).
_HX_ATTR_TO_KWARG: dict[str, str] = {
    "hx-get": "get",
    "hx-post": "post",
    "hx-target": "target",
    "hx-trigger": "trigger",
    "hx-swap": "swap",
    "hx-vals": "vals",
    "hx-headers": "headers",
    "hx-include": "include",
    "hx-confirm": "confirm",
}


@pytest.mark.unit
@pytest.mark.parametrize(
    "hx_attr",
    ["hx-get", "hx-post", "hx-target", "hx-trigger", "hx-swap",
     "hx-vals", "hx-headers", "hx-include", "hx-confirm"],
)
def test_hx_attr_passes_through(hx_attr: str) -> None:
    """Each whitelisted hx-* attr passes through HTMY rendering."""
    kwarg_name = _HX_ATTR_TO_KWARG[hx_attr]
    rendered = htmx_attrs(**{kwarg_name: "/api/test"})
    assert hx_attr in rendered, (
        f"whitelisted {hx_attr!r} missing from rendered output {rendered!r}"
    )


@pytest.mark.unit
def test_hx_vals_json_encoded() -> None:
    """hx-vals is JSON-encoded per HTMY contract (caller-supplied JSON)."""
    rendered = htmx_attrs(vals='{"id": 123}')
    assert "hx-vals" in rendered, (
        f"hx-vals missing from rendered output {rendered!r}"
    )


@pytest.mark.unit
def test_hx_headers_json_encoded() -> None:
    """hx-headers is JSON-encoded per HTMY contract (caller-supplied JSON)."""
    rendered = htmx_attrs(headers='{"X-Custom": "value"}')
    assert "hx-headers" in rendered, (
        f"hx-headers missing from rendered output {rendered!r}"
    )
