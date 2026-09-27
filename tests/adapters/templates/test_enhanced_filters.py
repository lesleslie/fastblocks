"""D1 coverage tests for fastblocks/adapters/templates/_enhanced_filters.py.

Targets the template-helper module: image filters (Cloudflare/TwicPics),
icon filters (Phosphor/Heroicons/Remix/Material/Kelp/WebAwesome),
font-loading helpers, and HTMX progressive-enhancement functions.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

import pytest

from fastblocks.adapters.templates._enhanced_filters import (
    AdapterStatus,
    cf_image_url,
    cf_responsive_image,
    font_face_declaration,
    heroicon,
    htmx_infinite_scroll_sentinel,
    htmx_progressive_enhancement,
    htmx_turbo_frame,
    kelp_card,
    kelp_component,
    material_icon,
    phosphor_icon,
    remix_icon,
    twicpics_image,
    twicpics_smart_crop,
    wa_icon,
    wa_icon_with_text,
)


# ---------------------------------------------------------------------------
# AdapterStatus
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestAdapterStatus:
    def test_status_values(self) -> None:
        assert AdapterStatus.STABLE == "STABLE"
        assert AdapterStatus.BETA == "BETA"


# ---------------------------------------------------------------------------
# Cloudflare image filters
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestCloudflareImageFilters:
    def test_cf_image_url_returns_string(self) -> None:
        # With no settings configured the helper returns a placeholder.
        url = cf_image_url("img-1")
        assert isinstance(url, str)

    def test_cf_responsive_image(self) -> None:
        out = cf_responsive_image(
            "img-1",
            "alt text",
            {
                "mobile": {"width": 400},
                "desktop": {"width": 1200},
            },
        )
        assert isinstance(out, str)


# ---------------------------------------------------------------------------
# TwicPics filters
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestTwicPicsFilters:
    def test_twicpics_image(self) -> None:
        out = twicpics_image("images/foo.jpg")
        assert isinstance(out, str)

    def test_twicpics_smart_crop(self) -> None:
        out = twicpics_smart_crop("images/foo.jpg", 200, 200, focus="auto")
        assert isinstance(out, str)


# ---------------------------------------------------------------------------
# Icon filters
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIconFilters:
    def test_wa_icon(self) -> None:
        out = wa_icon("home")
        assert "wa-" in out

    def test_wa_icon_with_text(self) -> None:
        out = wa_icon_with_text("home", "Home")
        assert "Home" in out

    def test_kelp_component(self) -> None:
        out = kelp_component("button", "Click me")
        assert "kelp-button" in out

    def test_kelp_component_with_attributes(self) -> None:
        out = kelp_component(
            "button",
            "Click",
            variant="primary",
            size="lg",
            **{"class": "extra"},
        )
        assert "kelp-button" in out

    def test_kelp_card(self) -> None:
        out = kelp_card("Title", "Body content")
        assert isinstance(out, str)

    def test_phosphor_icon_default(self) -> None:
        out = phosphor_icon("house")
        assert "ph-house" in out

    def test_phosphor_icon_bold(self) -> None:
        out = phosphor_icon("house", weight="bold")
        assert "ph-bold" in out

    def test_heroicon_outline(self) -> None:
        out = heroicon("home", style="outline")
        assert isinstance(out, str)

    def test_heroicon_solid(self) -> None:
        out = heroicon("home", style="solid")
        assert isinstance(out, str)

    def test_remix_icon(self) -> None:
        out = remix_icon("home")
        assert "ri-" in out

    def test_material_icon_default(self) -> None:
        out = material_icon("home")
        assert "material-icons" in out

    def test_material_icon_variant(self) -> None:
        out = material_icon("home", variant="outlined")
        assert "material-icons" in out


# ---------------------------------------------------------------------------
# Font-loading helpers
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFontHelpers:
    def test_font_face_declaration(self) -> None:
        # ``font_files`` is a dict mapping format -> URL.
        out = font_face_declaration(
            "Inter",
            {"woff2": "/fonts/inter.woff2"},
        )
        assert isinstance(out, str)

    def test_font_face_declaration_with_format(self) -> None:
        out = font_face_declaration(
            "Inter",
            {"woff2": "/fonts/inter.woff2", "truetype": "/fonts/inter.ttf"},
            weight="400",
            style="normal",
        )
        assert isinstance(out, str)


# ---------------------------------------------------------------------------
# HTMX progressive-enhancement filters
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestHtmxFilters:
    def test_htmx_progressive_enhancement(self) -> None:
        out = htmx_progressive_enhancement(
            "Click me",
            {"hx-get": "/endpoint", "hx-trigger": "click"},
        )
        assert isinstance(out, str)

    def test_htmx_turbo_frame(self) -> None:
        out = htmx_turbo_frame("main", src="/content")
        assert isinstance(out, str)

    def test_htmx_infinite_scroll_sentinel(self) -> None:
        out = htmx_infinite_scroll_sentinel("/more", container="#list")
        assert isinstance(out, str)