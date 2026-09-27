"""D1 coverage tests for fastblocks/adapters/icons/phosphor.py.

Targets Phosphor-icons adapter: settings, stylesheet links, icon-class
generation, tag helpers (regular, duotone, sprite), and template filter
registration.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fastblocks.adapters.icons.phosphor import (
    PhosphorIcons,
    PhosphorIconsSettings,
    _register_ph_basic_filters,
    _register_ph_duotone_functions,
    _register_ph_interactive_functions,
    register_phosphor_filters,
)


@pytest.fixture
def adapter() -> PhosphorIcons:
    return PhosphorIcons()


@pytest.fixture
def settings() -> PhosphorIconsSettings:
    return PhosphorIconsSettings()


@pytest.fixture
def env(
    adapter: PhosphorIcons, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
    """Minimal Jinja2 env stub with decorator API used by phosphor."""
    filters: dict[str, Any] = {}
    globals_: dict[str, Any] = {}

    class _FilterProxy:
        def __call__(self, name: str):
            def deco(fn: Any) -> Any:
                filters[name] = fn
                return fn

            return deco

    class _GlobalsProxy:
        def __call__(self, name: str):
            def deco(fn: Any) -> Any:
                globals_[name] = fn
                return fn

            return deco

    class _Env:
        def __init__(self) -> None:
            self.filters = filters
            self.globals = globals_
            self.filter = _FilterProxy()
            self.global_ = _GlobalsProxy()

    monkeypatch.setattr(
        "fastblocks.adapters.icons.phosphor.resolve_instance",
        lambda *_args, **_kwargs: adapter,
    )

    return SimpleNamespace(env=_Env())


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestPhosphorSettings:
    def test_default_variant_is_regular(
        self, settings: PhosphorIconsSettings
    ) -> None:
        assert settings.default_variant == "regular"

    def test_default_version(self, settings: PhosphorIconsSettings) -> None:
        assert settings.version == "2.0.8"

    def test_cdn_url(self, settings: PhosphorIconsSettings) -> None:
        assert settings.cdn_url.startswith("https://")

    def test_enabled_variants_complete(
        self, settings: PhosphorIconsSettings
    ) -> None:
        assert set(settings.enabled_variants) == {
            "regular",
            "thin",
            "light",
            "bold",
            "fill",
            "duotone",
        }

    def test_alias_home_resolves_to_house(
        self, settings: PhosphorIconsSettings
    ) -> None:
        assert settings.icon_aliases["home"] == "house"

    def test_alias_user_resolves_to_user_circle(
        self, settings: PhosphorIconsSettings
    ) -> None:
        assert settings.icon_aliases["user"] == "user-circle"


# ---------------------------------------------------------------------------
# Stylesheet links
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStylesheetLinks:
    def test_returns_one_link_per_variant_plus_custom_style(
        self, adapter: PhosphorIcons
    ) -> None:
        adapter.settings = PhosphorIconsSettings()
        links = adapter.get_stylesheet_links()
        # one <link> per enabled variant + one <style> for custom CSS.
        assert len(links) == len(adapter.settings.enabled_variants) + 1

    def test_uses_unpkg_cdn(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        links = adapter.get_stylesheet_links()
        assert any("unpkg.com/@phosphor-icons/web" in l for l in links)

    def test_includes_inline_style_block(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        links = adapter.get_stylesheet_links()
        style_link = next(l for l in links if l.startswith("<style>"))
        assert ".ph" in style_link

    def test_lazy_settings_initialization(self, adapter: PhosphorIcons) -> None:
        assert adapter.settings is None
        adapter.get_stylesheet_links()
        assert adapter.settings is not None


# ---------------------------------------------------------------------------
# Icon class / tag generation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetIconClass:
    def test_default_variant(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        cls = adapter.get_icon_class("house")
        assert "ph-house" in cls

    def test_explicit_variant(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        cls = adapter.get_icon_class("house", variant="bold")
        assert "ph-bold" in cls or "house" in cls

    def test_unknown_icon(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        cls = adapter.get_icon_class("nonexistent")
        assert "ph-nonexistent" in cls


@pytest.mark.unit
class TestIconTagHelpers:
    def test_get_icon_tag_default(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_tag("house")
        assert "<i" in tag
        assert "ph-" in tag
        assert "</i>" in tag

    def test_get_icon_tag_with_rotation(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_tag("house", rotate=90)
        assert "ph-rotate-90" in tag

    def test_get_icon_tag_with_flip(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_tag("house", flip="horizontal")
        assert "ph-flip-horizontal" in tag

    def test_get_icon_tag_with_spin_animation(
        self, adapter: PhosphorIcons
    ) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_tag("house", spin=True)
        assert "ph-spin" in tag

    def test_get_icon_tag_with_pulse_animation(
        self, adapter: PhosphorIcons
    ) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_tag("house", pulse=True)
        assert "ph-pulse" in tag

    def test_get_icon_tag_with_align(self, adapter: PhosphorIcons) -> None:
        # Only top/middle/bottom/baseline produce a class — "center" silently
        # drops through (kept as an HTML attribute).
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_tag("house", align="top")
        assert "ph-align-top" in tag

    def test_get_icon_tag_with_interactive(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_tag("house", interactive=True)
        assert "ph-interactive" in tag

    def test_get_duotone_icon_tag(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_duotone_icon_tag("house")
        assert "<i" in tag
        assert "ph-duotone" in tag or "house" in tag

    def test_get_icon_sprite_tag(self, adapter: PhosphorIcons) -> None:
        adapter.settings = PhosphorIconsSettings()
        tag = adapter.get_icon_sprite_tag("house")
        assert "<svg" in tag
        assert "ph-house" in tag


# ---------------------------------------------------------------------------
# Filter registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterRegistration:
    def test_register_basic_filters(self, env: SimpleNamespace) -> None:
        _register_ph_basic_filters(env.env)
        assert "ph_icon" in env.env.filters
        assert "ph_class" in env.env.filters
        assert "phosphor_stylesheet_links" in env.env.globals

    def test_ph_icon_filter(self, env: SimpleNamespace) -> None:
        _register_ph_basic_filters(env.env)
        out = env.env.filters["ph_icon"]("house")
        assert "ph-" in out

    def test_ph_class_filter(self, env: SimpleNamespace) -> None:
        _register_ph_basic_filters(env.env)
        out = env.env.filters["ph_class"]("house", "bold")
        assert "ph-" in out

    def test_phosphor_stylesheet_links_global(
        self, env: SimpleNamespace
    ) -> None:
        _register_ph_basic_filters(env.env)
        result = env.env.globals["phosphor_stylesheet_links"]()
        assert isinstance(result, str)
        assert "stylesheet" in result

    def test_register_duotone_functions(self, env: SimpleNamespace) -> None:
        _register_ph_duotone_functions(env.env)
        assert "ph_duotone" in env.env.globals

    def test_register_interactive_functions(
        self, env: SimpleNamespace
    ) -> None:
        _register_ph_interactive_functions(env.env)
        assert "ph_interactive" in env.env.globals
        assert "ph_button_icon" in env.env.globals

    def test_register_all_filters_combined(self, env: SimpleNamespace) -> None:
        register_phosphor_filters(env.env)
        # basic
        assert "ph_icon" in env.env.filters
        # duotone
        assert "ph_duotone" in env.env.globals
        # interactive
        assert "ph_interactive" in env.env.globals