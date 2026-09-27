"""D1 coverage tests for fastblocks/adapters/icons/materialicons.py.

Targets uncovered behavior of the MaterialIcons adapter:
- settings defaults (themes, aliases, sizes)
- stylesheet link generation for each theme variant
- ``get_icon_class`` + ``get_icon_tag`` with theme/size/density/transformation
- ``get_fab_tag`` (mini/extended)
- filter-registration functions on a Jinja2 ``Environment`` stub
"""
# pyright: reportAttributeAccessIssue=false, reportFunctionMemberAccess=false
from __future__ import annotations

from types import SimpleNamespace

import pytest

from fastblocks.adapters.icons.materialicons import (
    MaterialIcons,
    MaterialIconsSettings,
    _register_material_basic_filters,
    _register_material_button_functions,
    _register_material_chip_functions,
    _register_material_fab_functions,
    register_materialicons_filters,
)


@pytest.fixture
def adapter() -> MaterialIcons:
    return MaterialIcons()


@pytest.fixture
def settings() -> MaterialIconsSettings:
    return MaterialIconsSettings()


@pytest.fixture
def env(adapter: MaterialIcons, monkeypatch: pytest.MonkeyPatch) -> SimpleNamespace:
    """Minimal Jinja2 ``Environment`` stand-in with decorator API.

    The real adapter registers via ``@env.filter(name)`` / ``@env.global_(name)``,
    so the stub implements those decorator methods (the underlying dict is
    also exposed for ``len(filters)``-style introspection in real envs).
    """

    filters: dict[str, t.Any] = {}
    globals_: dict[str, t.Any] = {}

    class _FilterProxy:
        def __call__(self, name: str):
            def deco(fn: t.Any) -> t.Any:
                filters[name] = fn
                return fn

            return deco

    class _GlobalsProxy:
        def __call__(self, name: str):
            def deco(fn: t.Any) -> t.Any:
                globals_[name] = fn
                return fn

            return deco

    class _Env:
        def __init__(self) -> None:
            self.filters = filters
            self.globals = globals_
            self.filter = _FilterProxy()
            self.global_ = _GlobalsProxy()

    # Patch the icons resolution so the registered filters can find
    # a MaterialIcons instance — the real prod path uses Oneiric DI.
    monkeypatch.setattr(
        "fastblocks.adapters.icons.materialicons.resolve_instance",
        lambda *_args, **_kwargs: adapter,
    )

    return SimpleNamespace(env=_Env())


# ---------------------------------------------------------------------------
# Settings
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestMaterialIconsSettings:
    def test_default_theme_is_filled(self, settings: MaterialIconsSettings) -> None:
        assert settings.default_theme == "filled"

    def test_all_themes_enabled_by_default(
        self, settings: MaterialIconsSettings
    ) -> None:
        assert set(settings.enabled_themes) == {
            "filled",
            "outlined",
            "round",
            "sharp",
            "two-tone",
        }

    def test_alias_home_resolves_to_home(
        self, settings: MaterialIconsSettings
    ) -> None:
        assert settings.icon_aliases["home"] == "home"

    def test_alias_user_resolves_to_person(
        self, settings: MaterialIconsSettings
    ) -> None:
        assert settings.icon_aliases["user"] == "person"

    def test_default_size(self, settings: MaterialIconsSettings) -> None:
        assert settings.default_size == "24px"

    def test_module_metadata(self, settings: MaterialIconsSettings) -> None:
        assert settings.MODULE_STATUS == "stable"


# ---------------------------------------------------------------------------
# Stylesheet links
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStylesheetLinks:
    def test_returns_one_link_per_theme_plus_custom_style(
        self, adapter: MaterialIcons
    ) -> None:
        adapter.settings = MaterialIconsSettings()
        links = adapter.get_stylesheet_links()
        # One <link> per enabled theme + one <style> block for custom CSS.
        assert len(links) == len(adapter.settings.enabled_themes) + 1

    def test_filled_theme_uses_base_url(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings(enabled_themes=["filled"])
        links = adapter.get_stylesheet_links()
        assert any("family=Material+Icons" in link for link in links)
        assert any(
            "family=Material+Icons+Outlined" not in link for link in links
        )

    def test_outlined_theme_uses_themed_url(
        self, adapter: MaterialIcons
    ) -> None:
        adapter.settings = MaterialIconsSettings(enabled_themes=["outlined"])
        links = adapter.get_stylesheet_links()
        assert any("family=Material+Icons+Outlined" in link for link in links)

    def test_two_tone_theme_url_uses_plus(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings(enabled_themes=["two-tone"])
        links = adapter.get_stylesheet_links()
        assert any("Material+Icons+Two+Tone" in link for link in links)

    def test_includes_inline_style_block(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        links = adapter.get_stylesheet_links()
        style_link = next(l for l in links if l.startswith("<style>"))
        assert ".material-icons" in style_link
        assert "</style>" in style_link

    def test_lazy_settings_initialization(self, adapter: MaterialIcons) -> None:
        # settings is None at construction; first call populates it.
        assert adapter.settings is None
        adapter.get_stylesheet_links()
        assert adapter.settings is not None


# ---------------------------------------------------------------------------
# Icon class / tag generation
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetIconClass:
    def test_default_theme_produces_base_class(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        cls = adapter.get_icon_class("home")
        assert "material-icons" in cls
        # "filled" is the default — no extra theme class added.
        assert "filled" not in cls

    def test_explicit_theme_adds_class(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        cls = adapter.get_icon_class("home", theme="outlined")
        assert "material-icons-outlined" in cls

    def test_unknown_icon_uses_name_as_class(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        cls = adapter.get_icon_class("nonexistent-icon")
        assert "material-icons" in cls


@pytest.mark.unit
class TestGetIconTag:
    def test_basic_tag_includes_icon_class(
        self, adapter: MaterialIcons
    ) -> None:
        adapter.settings = MaterialIconsSettings()
        tag = adapter.get_icon_tag("home")
        assert "<span" in tag
        assert "material-icons" in tag
        assert "</span>" in tag

    def test_size_class_added_when_size_provided(
        self, adapter: MaterialIcons
    ) -> None:
        adapter.settings = MaterialIconsSettings()
        tag = adapter.get_icon_tag("home", size="48px")
        # Size is applied as inline style, not as a class.
        assert "font-size: 48px" in tag

    def test_existing_class_attribute_merged(
        self, adapter: MaterialIcons
    ) -> None:
        adapter.settings = MaterialIconsSettings()
        tag = adapter.get_icon_tag("home", **{"class": "extra-class"})
        assert "extra-class" in tag
        assert "material-icons" in tag

    def test_density_class_added(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        tag = adapter.get_icon_tag("home", density="dense")
        # Density= adds a "material-icons-dense" class on the icon.
        assert "material-icons-dense" in tag


# ---------------------------------------------------------------------------
# FAB tag
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestGetFabTag:
    def test_default_fab_class(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        tag = adapter.get_fab_tag("add")
        assert "fab" in tag

    def test_mini_fab_class(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        tag = adapter.get_fab_tag("add", mini=True)
        # ``mini`` is currently passed as a button attribute, not a class.
        assert 'mini="True"' in tag or "fab-mini" in tag

    def test_extended_fab_class(self, adapter: MaterialIcons) -> None:
        adapter.settings = MaterialIconsSettings()
        tag = adapter.get_fab_tag("add", extended=True)
        # ``extended`` is passed as a button attribute, not a class.
        assert 'extended="True"' in tag or "fab-extended" in tag


# ---------------------------------------------------------------------------
# Filter registration
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestFilterRegistration:
    def test_register_basic_filters_attaches_filters(
        self, env: SimpleNamespace
    ) -> None:
        _register_material_basic_filters(env.env)
        assert "material_icon" in env.env.filters
        assert "material_class" in env.env.filters

    def test_register_basic_filters_attaches_stylesheet_global(
        self, env: SimpleNamespace
    ) -> None:
        _register_material_basic_filters(env.env)
        assert "materialicons_stylesheet_links" in env.env.globals

    def test_material_icon_filter(self, env: SimpleNamespace) -> None:
        _register_material_basic_filters(env.env)
        out = env.env.filters["material_icon"]("home")
        assert "material-icons" in out

    def test_material_class_filter(self, env: SimpleNamespace) -> None:
        _register_material_basic_filters(env.env)
        out = env.env.filters["material_class"]("home", "outlined")
        assert "material-icons-outlined" in out

    def test_stylesheet_links_global(self, env: SimpleNamespace) -> None:
        _register_material_basic_filters(env.env)
        links = env.env.globals["materialicons_stylesheet_links"]()
        assert isinstance(links, str)
        assert "rel=\"stylesheet\"" in links

    def test_register_fab_function(self, env: SimpleNamespace) -> None:
        _register_material_fab_functions(env.env)
        assert "material_fab" in env.env.globals
        tag = env.env.globals["material_fab"]("add")
        assert "fab" in tag

    def test_register_button_functions(self, env: SimpleNamespace) -> None:
        _register_material_button_functions(env.env)
        assert "material_button" in env.env.globals

    def test_register_chip_functions(self, env: SimpleNamespace) -> None:
        _register_material_chip_functions(env.env)
        assert "material_chip" in env.env.globals

    def test_register_all_filters_combined(self, env: SimpleNamespace) -> None:
        register_materialicons_filters(env.env)
        # basic
        assert "material_icon" in env.env.filters
        # fab
        assert "material_fab" in env.env.globals
        # button
        assert "material_button" in env.env.globals
        # chip
        assert "material_chip" in env.env.globals