"""Tests for the fastblocks-ui style adapter (WS-17).

Requires the optional `fastblocks-ui` package (see the `fastblocks_ui`
dependency group in pyproject.toml) — skipped entirely if it isn't
installed, matching the adapter's own lazy, optional-dependency import.
"""

from __future__ import annotations

import typing as t

import pytest

fastblocks_ui = pytest.importorskip("fastblocks_ui")

from fastblocks.adapters.style.fastblocks_ui import (  # noqa: E402
    FastBlocksUIStyle,
    FastBlocksUIStyleSettings,
    register_fastblocks_ui_functions,
)


@pytest.mark.unit
class TestFastBlocksUIStyleSettings:
    def test_settings_defaults(self):
        settings = FastBlocksUIStyleSettings()
        assert settings.static_mount == "/static/fastblocks-ui"
        assert settings.cache_bust is True


@pytest.mark.unit
class TestFastBlocksUIStyle:
    def test_get_component_class_known_component(self):
        style = FastBlocksUIStyle()
        assert style.get_component_class("button") == "ui-button"
        assert style.get_component_class("card") == "ui-card"
        assert style.get_component_class("dialog") == "ui-dialog"

    def test_get_component_class_state_modifier_passthrough(self):
        """State modifiers (`is-primary`, ...) are already real class tokens
        for fastblocks-ui — there's nothing to translate, unlike Kelp/Web
        Awesome/Vanilla, which map semantic names to their own prefixed
        classes."""
        style = FastBlocksUIStyle()
        assert style.get_component_class("is-primary") == "is-primary"
        assert style.get_component_class("is-large") == "is-large"

    def test_get_component_class_unknown_passthrough(self):
        style = FastBlocksUIStyle()
        assert style.get_component_class("something-custom") == "something-custom"

    def test_get_component_class_empty(self):
        style = FastBlocksUIStyle()
        assert style.get_component_class("") == ""

    def test_get_stylesheet_links_points_at_real_shipped_css(self):
        style = FastBlocksUIStyle()
        links = style.get_stylesheet_links()
        assert len(links) == 1
        assert "fastblocks-ui.css" in links[0]
        assert links[0].startswith(
            '<link rel="stylesheet" href="/static/fastblocks-ui/css/fastblocks-ui.css'
        )

    def test_get_script_tags_points_at_real_shipped_js(self):
        style = FastBlocksUIStyle()
        tags = style.get_script_tags()
        assert len(tags) == 1
        assert "fastblocks-ui.js" in tags[0]

    def test_cache_busting_uses_real_installed_version(self):
        style = FastBlocksUIStyle()
        links = style.get_stylesheet_links()
        assert f"?v={fastblocks_ui.__version__}" in links[0]

    def test_cache_busting_can_be_disabled(self):
        style = FastBlocksUIStyle()
        style.settings.cache_bust = False
        links = style.get_stylesheet_links()
        assert "?v=" not in links[0]


@pytest.mark.unit
class TestRegisterFastBlocksUIFunctions:
    """Prove the Jinja wiring actually works end-to-end.

    WS-17 explicitly asked for this adapter to "actually get invoked via the
    mechanism established in step 1, with a test proving it (not just
    defined-and-hoped-for like the existing three)" — this class is that
    test. It uses a plain, real `jinja2.Environment` rather than FastBlocks'
    async-Jinja stack: `register_fastblocks_ui_functions` only touches
    `env.globals`/`env.filters`, the same real dict attributes a plain
    `jinja2.Environment` exposes (this is also why `register_kelp_functions`'
    `@env.global_(...)`/`@env.filter(...)` calls would fail against a real
    environment of either kind — see that function's docstring).
    """

    def _env(self) -> t.Any:
        import jinja2

        env = jinja2.Environment(autoescape=False)
        register_fastblocks_ui_functions(env)
        return env

    def test_registers_real_dict_entries(self):
        env = self._env()
        assert "fastblocks_ui_stylesheet_links" in env.globals
        assert "fastblocks_ui_script_tags" in env.globals
        assert "fastblocks_ui_class" in env.filters
        assert "ui_button" in env.globals
        assert "ui_card" in env.globals
        assert "ui_field" in env.globals
        assert "ui_alert" in env.globals
        assert "ui_container" in env.globals

    def test_stylesheet_links_global_renders(self):
        env = self._env()
        template = env.from_string("{{ fastblocks_ui_stylesheet_links() }}")
        assert "fastblocks-ui.css" in template.render()

    def test_class_filter_renders_real_manifest_class(self):
        env = self._env()
        template = env.from_string('{{ "button"|fastblocks_ui_class }}')
        assert template.render() == "ui-button"

    def test_ui_button_global_matches_real_helper_output(self):
        env = self._env()
        template = env.from_string('{{ ui_button("Save", variant="primary") }}')
        assert template.render() == str(
            fastblocks_ui.button("Save", variant="primary")
        )

    def test_ui_card_global_matches_real_helper_output(self):
        env = self._env()
        template = env.from_string('{{ ui_card(body="Body text") }}')
        assert template.render() == str(fastblocks_ui.card(body="Body text"))


# ---------------------------------------------------------------------------
# Audit regressions (2026-07-27)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestStyleAdapterAssetWiring:
    """The shipped assets must actually be loadable and renderable."""

    def test_script_tag_loads_the_bundle_as_a_module(self) -> None:
        """`fastblocks-ui.js` is an ES module and needs `type="module"`.

        It is `export { ... } from './enhance.js'`. Served as a classic
        script the browser raises `SyntaxError: Unexpected token 'export'`
        and the entire JS enhancement layer never initialises -- tabs,
        dialogs and menus silently lose their behaviour.
        """
        from fastblocks.adapters.style.fastblocks_ui import FastBlocksUIStyle

        tags = FastBlocksUIStyle().get_script_tags()

        assert tags, "no script tags emitted"
        joined = "\n".join(tags)
        assert 'type="module"' in joined, (
            f"ES module served as a classic script: {joined}"
        )

    def test_ui_globals_preserve_html_safety(self) -> None:
        """`ui_*` globals must keep `__html__` so autoescape leaves them alone.

        `starlette_async_jinja` enables autoescape, and wrapping the helper
        output in `str()` discards `SafeHTML.__html__`. Jinja then escapes the
        markup and the page shows literal `&lt;button ...&gt;` source text.
        """
        import jinja2

        from fastblocks.adapters.style.fastblocks_ui import (
            register_fastblocks_ui_functions,
        )

        env = jinja2.Environment(autoescape=True)
        register_fastblocks_ui_functions(env)

        rendered = env.from_string('{{ ui_button("Save", variant="primary") }}').render()

        assert "<button" in rendered, f"markup was escaped into text: {rendered!r}"
        assert "&lt;button" not in rendered
