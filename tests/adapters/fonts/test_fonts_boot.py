"""D3: boot test for the squirrel font adapter.

Key: ``("fastblocks", "font_squirrel")`` (verified at
``fonts/squirrel.py:55``).
NOT ``("fastblocks", "fonts")`` — that resolves to the abstract base.
API: ``get_font_import()`` (async, returns @font-face import CSS) and
``get_font_family(font_type)`` — NOT ``get_font_face_css()``.
"""
from __future__ import annotations

import pytest

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)


@pytest.fixture
def fonts_adapter(fresh_registry):
    from fastblocks.adapters.fonts.squirrel import FontSquirrelFonts

    instance = FontSquirrelFonts()
    # The default FontSquirrelFontsSettings ships an empty ``fonts``
    # list, so ``get_font_import()`` returns the documented no-fonts
    # comment instead of ``@font-face`` declarations. Configure a
    # single self-hosted font so the @font-face assertion has
    # something real to verify against.
    instance.settings.fonts = [
        {
            "family": "Inter",
            "type": "primary",
            "weight": "400",
            "style": "normal",
            "path": "/fonts/inter-400.woff2",
        },
    ]
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="font_squirrel",
        factory=lambda: instance,
        metadata={"class": "FontSquirrelFonts"},
    )
    return resolve_instance(fresh_registry, "fastblocks", "font_squirrel")


def test_fonts_adapter_resolves(fonts_adapter):
    assert fonts_adapter is not None


@pytest.mark.asyncio
async def test_fonts_adapter_provides_font_import_css(fonts_adapter):
    """Contract: squirrel's ``get_font_import()`` returns CSS containing
    ``@font-face`` for a configured self-hosted font.

    When ``settings.fonts`` is empty the adapter returns a documented
    HTML comment (``<!-- No self-hosted fonts configured -->``) — that
    branch is exercised by
    ``test_fonts_adapter_provides_empty_fonts_comment`` below.
    """
    css = await fonts_adapter.get_font_import()
    assert isinstance(css, str)
    assert "@font-face" in css, (
        f"D3: fonts adapter returned CSS without @font-face: {css!r}"
    )


@pytest.mark.asyncio
async def test_fonts_adapter_provides_empty_fonts_comment(fresh_registry):
    """Document the no-fonts branch: with empty ``settings.fonts`` the
    adapter returns the explicit HTML comment so consumers can tell
    "no fonts" apart from a malformed CSS string."""
    from fastblocks.adapters.fonts.squirrel import FontSquirrelFonts

    empty = FontSquirrelFonts()
    empty.settings.fonts = []
    css = await empty.get_font_import()
    assert "No self-hosted fonts configured" in css, (
        f"D3: empty-fonts branch returned unexpected output: {css!r}"
    )


def test_fonts_adapter_provides_font_family(fonts_adapter):
    """Contract: ``get_font_family(font_type)`` returns a string."""
    family = fonts_adapter.get_font_family("primary")
    assert isinstance(family, str) and family, (
        f"D3: fonts adapter returned empty family for 'primary'"
    )
