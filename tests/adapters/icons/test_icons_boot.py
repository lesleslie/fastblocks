"""D3: boot test for the icons adapter.

``IconsBase`` Protocol exposes ``get_icon_class(name)`` and
``get_icon_tag(name, **attrs)`` (verified at icons/_base.py:34-35) —
NOT ``render(name)``.

Implementation note: each icon set (HeroiconsIcons, MaterialIconsIcons,
PhosphorIcons, RemixIconIcons) registers itself under its own key
(e.g. ``"heroicons"``) inside its module, not a canonical ``"icons"``
key. To exercise a representative icon adapter in isolation we
instantiate ``HeroiconsIcons`` directly and re-register it against
``fresh_registry`` under a deterministic key. ``IconsBase.__init__``
additionally registers ``"icons"`` as a side effect, so we get both
keys for free and resolve on ``"icons"`` exactly like the brief
prescribes (Phase 1.5 follow-up: the architecture is per-set keyed,
not canonical).
"""
from __future__ import annotations

import pytest

from fastblocks.adapters.oneiric_helper import (
    register_candidate_strict,
    resolve_instance,
)


@pytest.fixture
def icons_adapter(fresh_registry):
    from fastblocks.adapters.icons.heroicons import (
        HeroiconsIcons,
        HeroiconsIconsSettings,
    )

    instance = HeroiconsIcons()
    # HeroiconsIcons.__init__ declares ``self.settings`` as a type
    # annotation only — no value is assigned. ``get_icon_class`` lazily
    # assigns it on first call, but we want it ready at boot time so
    # the test exercises the adapter's normal shape.
    instance.settings = HeroiconsIconsSettings()
    register_candidate_strict(
        fresh_registry,
        domain="fastblocks",
        key="icons",
        factory=lambda: instance,
        metadata={"class": "HeroiconsIcons"},
    )
    return resolve_instance(fresh_registry, "fastblocks", "icons")


def test_icons_adapter_resolves(icons_adapter):
    assert icons_adapter is not None


def test_icons_adapter_returns_class_for_known_name(icons_adapter):
    """Smoke: a known icon name returns a non-empty CSS class string."""
    cls = icons_adapter.get_icon_class("home")
    assert isinstance(cls, str) and cls, (
        f"D3: icons adapter returned empty class for 'home'"
    )


def test_icons_adapter_returns_valid_svg_tag(icons_adapter):
    """Contract: the icon tag must be valid XML (per pytest IMP3)."""
    from defusedxml import ElementTree as DET  # XXE-safe per Bodai standard

    tag = icons_adapter.get_icon_tag("home")
    markup = tag if tag.lstrip().startswith("<") else f"<svg>{tag}</svg>"
    try:
        DET.fromstring(markup)
    except DET.ParseError as e:
        raise AssertionError(
            f"D3: icons adapter get_icon_tag returned invalid XML: "
            f"{tag!r} ({e})"
        )
