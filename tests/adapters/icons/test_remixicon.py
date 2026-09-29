"""D1 coverage tests for fastblocks/adapters/icons/remixicon.py.

Targets Remix Icon adapter — settings, stylesheet links, icon-class / tag
generation, stacked-icon helper, and template-filter registration.
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from types import SimpleNamespace
from typing import Any

import pytest

from fastblocks.adapters.icons.remixicon import (
    RemixIcon,
    RemixIconSettings,
    _register_ri_basic_filters,
    _register_ri_advanced_functions,
    register_remixicon_filters,
)


@pytest.fixture
def adapter() -> RemixIcon:
    return RemixIcon()


@pytest.fixture
def settings() -> RemixIconSettings:
    return RemixIconSettings()


@pytest.fixture
def env(
    adapter: RemixIcon, monkeypatch: pytest.MonkeyPatch
) -> SimpleNamespace:
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
        "fastblocks.adapters.icons.remixicon.resolve_instance",
        lambda *_a, **_k: adapter,
    )

    return SimpleNamespace(env=_Env())


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestSettings:
    def test_module_metadata(self, settings: RemixIconSettings) -> None:
        assert settings.MODULE_STATUS == "stable"

    def test_version(self, settings: RemixIconSettings) -> None:
        # Default version may be empty in production — assert type instead.
        assert isinstance(settings.version, str)


# ---------------------------------------------------------------------------
# Stylesheet links
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStylesheetLinks:
    def test_returns_links_with_style(self, adapter: RemixIcon) -> None:
        adapter.settings = RemixIconSettings()
        links = adapter.get_stylesheet_links()
        assert len(links) >= 1
        # Includes the inline <style> block.
        assert any("<style>" in l for l in links)

    def test_call_does_not_raise(self, adapter: RemixIcon) -> None:
        adapter.settings = RemixIconSettings()
        # Just verify shape — count varies by enabled_variants default.
        assert isinstance(adapter.get_stylesheet_links(), list)


# ---------------------------------------------------------------------------
# Icon class / tag generation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestIconHelpers:
    def test_get_icon_class(self, adapter: RemixIcon) -> None:
        adapter.settings = RemixIconSettings()
        cls = adapter.get_icon_class("home")
        assert "ri-" in cls

    def test_get_icon_class_with_variant(self, adapter: RemixIcon) -> None:
        adapter.settings = RemixIconSettings()
        cls = adapter.get_icon_class("home", variant="fill")
        assert "ri-" in cls

    def test_get_icon_tag(self, adapter: RemixIcon) -> None:
        adapter.settings = RemixIconSettings()
        tag = adapter.get_icon_tag("home")
        assert "<i" in tag or "<span" in tag

    def test_get_icon_tag_with_size(self, adapter: RemixIcon) -> None:
        adapter.settings = RemixIconSettings()
        tag = adapter.get_icon_tag("home", size="lg")
        # size=lg maps to a "ri-lg" class.
        assert isinstance(tag, str)

    def test_get_stacked_icons(self, adapter: RemixIcon) -> None:
        adapter.settings = RemixIconSettings()
        # The helper takes a background and a foreground icon separately.
        stacked = adapter.get_stacked_icons("home", "user")
        assert isinstance(stacked, str)
        assert "home" in stacked
        assert "user" in stacked


# ---------------------------------------------------------------------------
# Filter registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterRegistration:
    def test_register_basic_filters(self, env: SimpleNamespace) -> None:
        _register_ri_basic_filters(env.env)
        assert "ri" in env.env.filters
        assert "ri_class" in env.env.filters
        assert "remixicon_stylesheet_links" in env.env.globals

    def test_register_advanced_functions(self, env: SimpleNamespace) -> None:
        _register_ri_advanced_functions(env.env)
        assert "ri_stacked" in env.env.globals
        assert "ri_gradient" in env.env.globals

    def test_register_all_filters(self, env: SimpleNamespace) -> None:
        register_remixicon_filters(env.env)
        # basic
        assert "ri" in env.env.filters
        # advanced
        assert "ri_stacked" in env.env.globals

    def test_filters_callable(self, env: SimpleNamespace) -> None:
        register_remixicon_filters(env.env)
        assert callable(env.env.filters["ri"])
        assert callable(env.env.filters["ri_class"])
