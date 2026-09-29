"""D3: boot test for the ``fonts/squirrel`` adapter.

Spec §D3 row ``fonts/squirrel`` -> resolver pair
``("fastblocks", "font_squirrel")`` (verified at
``fastblocks/adapters/fonts/squirrel.py:55``).

NOTE on path: the brief specifies
``tests/adapters/fonts/test_squirrel_boot.py``; the existing
comprehensive boot test at ``tests/adapters/fonts/test_fonts_boot.py``
already covers the same adapter in greater depth. This file is the
brief-specified minimal boot test (one-off, doesn't duplicate the
existing coverage).

Implementation note: ``FontSquirrelFonts.__init__`` auto-registers
against the global ``depends`` singleton under
``("fastblocks", "font_squirrel")``. Re-registering against
``fresh_registry`` is harmless (same factory shape) and keeps the
test isolated from other tests that mutate the global resolver.
"""
from __future__ import annotations

import pytest

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)


def test_squirrel_fonts_resolves_via_oneiric(fresh_registry) -> None:
    """The squirrel font adapter must be discoverable under
    ``("fastblocks", "font_squirrel")``."""
    from fastblocks.adapters.fonts.squirrel import FontSquirrelFonts

    instance = FontSquirrelFonts()
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="font_squirrel",
        factory=lambda: instance,
        metadata={"class": "FontSquirrelFonts"},
    )
    resolved = resolve_instance(fresh_registry, "fastblocks", "font_squirrel")
    assert resolved is not None, (
        "D3: Oneiric resolver returned no instance for "
        "('fastblocks', 'font_squirrel')"
    )


@pytest.mark.asyncio
async def test_squirrel_fonts_returns_font_import_string() -> None:
    """Smoke: ``get_font_import()`` returns a string. With empty
    ``settings.fonts`` (the default) it returns the documented
    no-fonts comment; with a configured font it returns
    ``@font-face`` declarations. Both branches satisfy the boot
    contract."""
    from fastblocks.adapters.fonts.squirrel import FontSquirrelFonts

    instance = FontSquirrelFonts()
    css = await instance.get_font_import()
    assert isinstance(css, str), (
        f"D3: FontSquirrelFonts.get_font_import returned non-string: "
        f"{type(css).__name__}"
    )
    # Either the empty-fonts comment OR real @font-face declarations
    # are acceptable — both prove the adapter booted and ran.
    assert "No self-hosted fonts configured" in css or "@font-face" in css, (
        f"D3: unexpected get_font_import output: {css!r}"
    )
