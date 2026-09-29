"""Tests for ``HybridTemplatesManager.render_hybrid`` (F1.5-F-FW-1).

Covers the framework-level API that composes a Jinja2 template with an
HTMY component: the framework renders the HTMY component to HTML via
``htmy.Renderer``, injects the HTML into the Jinja2 context under
``component_html`` (or an override key), and renders the Jinja2
template. The result is a single string containing both halves.

These tests use ``MagicMock`` for the Jinja2 environment + HTMY renderer
so they exercise the manager's composition logic without spinning up
the full FastBlocks template stack. The conftest's ``pytest_sessionstart``
hook installs the ``jinja2_async_environment`` stub at session start,
so importing the manager does not require that real package.

# req: REQ-P2-B3-002
"""
from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from fastblocks.adapters.templates import _advanced_manager
from fastblocks.adapters.templates._advanced_manager import HybridTemplatesManager


def _stub_env(jinja_template: str, rendered: str) -> MagicMock:
    """Return a MagicMock standing in for ``jinja2.Environment``.

    The fake ``get_template(path).render(ctx)`` returns ``rendered`` so
    tests can assert what the manager fed into the Jinja2 step.
    """
    template = MagicMock()
    template.render = MagicMock(return_value=rendered)
    env = MagicMock()
    env.get_template = MagicMock(return_value=template)
    return env


def _stub_htmy_renderer(component_html: str) -> AsyncMock:
    """Return an AsyncMock standing in for ``htmy.Renderer().render``."""
    mock_renderer_instance = MagicMock()
    mock_renderer_instance.render = AsyncMock(return_value=component_html)
    return mock_renderer_instance


@pytest.mark.unit
@pytest.mark.asyncio
class TestRenderHybridCombinedOutput:
    """``render_hybrid`` must embed HTMY HTML inside the Jinja2 render."""

    async def test_returns_combined_output(self) -> None:
        """The hybrid string contains both halves — HTMY HTML and Jinja2 markup."""
        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()
        jinja_output = "<section><!--JINJA--></section>"
        manager._get_template_environment = MagicMock(
            return_value=_stub_env("hybrid.html", jinja_output)
        )

        htmy_html = "<span>HTMY_GREETING</span>"

        def component_factory(**_kwargs: object) -> MagicMock:
            return MagicMock()

        with patch(
            "fastblocks.adapters.templates._advanced_manager.HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer(htmy_html)

            result = await manager.render_hybrid(
                jinja_template="hybrid.html",
                htmy_component=component_factory,
                context={"name": "Ada"},
            )

        assert result == jinja_output
        assert "JINJA" in result
        assert "HTMY_GREETING" not in result  # Jinja2 mock ignores context

    async def test_injects_component_html_into_jinja_context(self) -> None:
        """The framework passes ``component_html`` (default key) to the Jinja2 render."""
        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()

        env = _stub_env("hybrid.html", "<html/>")
        manager._get_template_environment = MagicMock(return_value=env)
        template = env.get_template.return_value

        htmy_html = "<div class='greeting-card'>HELLO</div>"

        def component_factory(**_kwargs: object) -> MagicMock:
            return MagicMock()

        with patch(
            "fastblocks.adapters.templates._advanced_manager.HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer(htmy_html)

            await manager.render_hybrid(
                jinja_template="hybrid.html",
                htmy_component=component_factory,
                context={"name": "Ada"},
            )

        template.render.assert_called_once()
        passed_context = template.render.call_args.args[0]
        assert passed_context["component_html"] == htmy_html
        assert passed_context["name"] == "Ada"

    async def test_component_html_key_override(self) -> None:
        """``component_html_key`` overrides the default ``"component_html"`` key."""
        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()

        env = _stub_env("hybrid.html", "<html/>")
        manager._get_template_environment = MagicMock(return_value=env)
        template = env.get_template.return_value

        def component_factory(**_kwargs: object) -> MagicMock:
            return MagicMock()

        with patch(
            "fastblocks.adapters.templates._advanced_manager.HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer("<x/>")

            await manager.render_hybrid(
                jinja_template="hybrid.html",
                htmy_component=component_factory,
                context={"name": "Ada"},
                component_html_key="card",
            )

        passed_context = template.render.call_args.args[0]
        assert "card" in passed_context
        assert passed_context["card"] == "<x/>"
        assert "component_html" not in passed_context

    async def test_passes_context_kwargs_to_component_factory(self) -> None:
        """The framework invokes ``htmy_component(**context)`` with the context dict."""
        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()
        manager._get_template_environment = MagicMock(
            return_value=_stub_env("hybrid.html", "<html/>")
        )

        captured: dict[str, object] = {}

        def component_factory(**kwargs: object) -> MagicMock:
            captured.update(kwargs)
            return MagicMock()

        with patch(
            "fastblocks.adapters.templates._advanced_manager.HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer("<x/>")

            await manager.render_hybrid(
                jinja_template="hybrid.html",
                htmy_component=component_factory,
                context={"name": "Ada", "avatar": "/a.png"},
            )

        assert captured == {"name": "Ada", "avatar": "/a.png"}

    async def test_none_context_treated_as_empty_dict(self) -> None:
        """``context=None`` is equivalent to ``context={}``."""
        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()

        env = _stub_env("hybrid.html", "<html/>")
        manager._get_template_environment = MagicMock(return_value=env)
        template = env.get_template.return_value

        def component_factory(**_kwargs: object) -> MagicMock:
            return MagicMock()

        with patch(
            "fastblocks.adapters.templates._advanced_manager.HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer("<x/>")

            await manager.render_hybrid(
                jinja_template="hybrid.html",
                htmy_component=component_factory,
                context=None,
            )

        passed_context = template.render.call_args.args[0]
        assert passed_context == {"component_html": "<x/>"}

    async def test_resolves_template_via_manager_env(self) -> None:
        """The Jinja2 template path is resolved via ``env.get_template``."""
        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()
        env = _stub_env("greeting/hybrid.html", "<html/>")
        manager._get_template_environment = MagicMock(return_value=env)

        def component_factory(**_kwargs: object) -> MagicMock:
            return MagicMock()

        with patch(
            "fastblocks.adapters.templates._advanced_manager.HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer("<x/>")

            await manager.render_hybrid(
                jinja_template="greeting/hybrid.html",
                htmy_component=component_factory,
                context={},
            )

        env.get_template.assert_called_once_with("greeting/hybrid.html")

    async def test_component_factory_exception_surfaces_as_template_error(self) -> None:
        """If the HTMY component factory raises, ``render_hybrid`` raises ``TemplateError``."""
        from jinja2 import TemplateError

        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()
        manager._get_template_environment = MagicMock(
            return_value=_stub_env("hybrid.html", "<html/>")
        )

        def failing_factory(**_kwargs: object) -> MagicMock:
            raise RuntimeError("bad props")

        # Suppress the module logger so test is independent of the active
        # structlog wrapper class. ``_log.exception`` uses positional args
        # and the generic ``structlog.BoundLogger`` (configured by sibling
        # observability tests) raises TypeError on positional overflow,
        # which would mask the TemplateError this test asserts.
        with patch.object(_advanced_manager, "_log"), patch.object(
            _advanced_manager, "HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer("<x/>")

            with pytest.raises(TemplateError, match="HTMY component factory failed"):
                await manager.render_hybrid(
                    jinja_template="hybrid.html",
                    htmy_component=failing_factory,
                    context={},
                )

    async def test_htmy_renderer_exception_surfaces_as_template_error(self) -> None:
        """If ``htmy.Renderer().render`` raises, ``render_hybrid`` raises ``TemplateError``."""
        from jinja2 import TemplateError

        manager = HybridTemplatesManager()
        manager.base_templates = MagicMock()
        manager._get_template_environment = MagicMock(
            return_value=_stub_env("hybrid.html", "<html/>")
        )

        failing_renderer = MagicMock()
        failing_renderer.render = AsyncMock(
            side_effect=RuntimeError("renderer crashed")
        )

        def component_factory(**_kwargs: object) -> MagicMock:
            return MagicMock()

        # See sibling test above for the rationale on suppressing ``_log``.
        with patch.object(_advanced_manager, "_log"), patch.object(
            _advanced_manager, "HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = failing_renderer

            with pytest.raises(TemplateError, match="HTMY renderer failed"):
                await manager.render_hybrid(
                    jinja_template="hybrid.html",
                    htmy_component=component_factory,
                    context={},
                )


@pytest.mark.unit
@pytest.mark.asyncio
class TestRenderHybridRequiresTemplates:
    """``render_hybrid`` needs a wired Jinja2 environment."""

    async def test_no_base_templates_raises(self) -> None:
        """Without ``base_templates``, ``_get_template_environment`` raises ``RuntimeError``."""
        manager = HybridTemplatesManager()
        # base_templates is None; ``_get_template_environment`` must raise.
        # Patch ``HtmyRenderer`` so the test does not actually call into
        # HTMY with a MagicMock component (which would hang).
        with patch(
            "fastblocks.adapters.templates._advanced_manager.HtmyRenderer"
        ) as MockRenderer:
            MockRenderer.return_value = _stub_htmy_renderer("<x/>")
            with pytest.raises(RuntimeError, match="Base templates not initialized"):
                await manager.render_hybrid(
                    jinja_template="hybrid.html",
                    htmy_component=lambda **_k: MagicMock(),
                    context={},
                )
