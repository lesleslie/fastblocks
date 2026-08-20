"""``fastblocks-ui`` style adapter — the first style adapter actually wired end-to-end.

Unlike ``kelp.py``/``webawesome.py``, which hand-roll their own CSS as Python
f-strings and reimplement a semantic-name → framework-class translation
table, ``fastblocks-ui`` ships its own tested, versioned CSS/JS bundle and
Python helpers as a separate package. This adapter's job is just to *wire*
that existing, real package into a FastBlocks app — resolve the real shipped
asset paths, delegate class-name lookups to the real component manifest, and
delegate rendering to the real (already-escaping) ``fastblocks_ui`` helpers,
rather than reimplementing any of that here.

``fastblocks_ui`` is an optional dependency of ``fastblocks`` — this module
imports it lazily (inside functions, not at module scope) so that installing
``fastblocks`` alone doesn't require installing ``fastblocks-ui``, matching
how the ``admin`` style's optional ``sqladmin`` import is handled in
``adapters/templates/jinja2.py``.

See ``fastblocks-ui``'s cross-repo remediation plan, WS-17, for the full
rationale, including why the existing Kelp/Web Awesome adapters were found
to be disconnected scaffolding (``register_kelp_functions``/
``register_webawesome_functions`` have zero call sites anywhere in the
framework) rather than a working pattern to copy, and why this adapter uses
``fastblocks.core.style_registry``/``fastblocks.core.resolver.get_resolver``/
``fastblocks.adapters.oneiric_helper.register_candidate`` — the project's
actual documented conventions — instead of the ad hoc per-module
``Resolver()`` instance the three pre-existing style adapters use.
"""

from __future__ import annotations

import typing as t
from contextlib import suppress
from uuid import UUID

from ._base import StyleBase, StyleBaseSettings


class FastBlocksUIStyleSettings(StyleBaseSettings):
    """Settings for the fastblocks-ui style adapter."""

    MODULE_ID: UUID = UUID("01937d86-fb01-7e11-9c22-fa5760c11c55")  # Static UUID7
    MODULE_STATUS: str = "stable"

    # Mount point the app registers fastblocks-ui's static assets under —
    # must match whatever `StaticFiles(...)` mount the app actually uses.
    static_mount: str = "/static/fastblocks-ui"
    cache_bust: bool = True


class FastBlocksUIStyle(StyleBase):
    """Style adapter delegating to the real, installed ``fastblocks-ui`` package."""

    MODULE_ID: UUID = UUID("01937d86-fb01-7e11-9c22-fa5760c11c55")  # Static UUID7
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        super().__init__()
        self.settings = FastBlocksUIStyleSettings()
        self._component_classes: dict[str, str] | None = None

    def _fastblocks_ui(self) -> t.Any:
        """Import the real ``fastblocks_ui`` package (lazy, optional dependency)."""
        import fastblocks_ui

        return fastblocks_ui

    def _asset_url(self, filename: str, subdir: str) -> str:
        suffix = ""
        if self.settings.cache_bust:
            suffix = f"?v={self._fastblocks_ui().__version__}"
        return f"{self.settings.static_mount}/{subdir}/{filename}{suffix}"

    def get_stylesheet_links(self) -> list[str]:
        """Return a real ``<link>`` to the actual shipped, tested CSS bundle.

        Unlike ``kelp.py``/``webawesome.py``, which build a hand-rolled
        inline ``<style>`` block reimplementing their design system as an
        f-string, this resolves the real on-disk filename
        (``fastblocks_ui.get_css_path()``) so it can never drift from what
        the installed package actually ships.
        """
        import os

        css_path = self._fastblocks_ui().get_css_path()
        href = self._asset_url(os.path.basename(css_path), "css")
        return [f'<link rel="stylesheet" href="{href}">']

    def get_script_tags(self) -> list[str]:
        """Return a ``<script>`` tag for the shipped, optional JS enhancement layer."""
        import os

        js_path = self._fastblocks_ui().get_js_path()
        src = self._asset_url(os.path.basename(js_path), "js")
        # `type="module"` is required, not optional: `fastblocks-ui.js` is an
        # ES module (`export { ... } from './enhance.js'`). Loaded as a classic
        # script the browser throws `SyntaxError: Unexpected token 'export'`
        # before executing anything, so the whole enhancement layer -- tabs,
        # dialogs, menus -- silently never initialises.
        #
        # `defer` is dropped because module scripts are deferred by definition;
        # the attribute is ignored on them.
        return [f'<script type="module" src="{src}"></script>']

    def _classes(self) -> dict[str, str]:
        """``name`` -> ``class_name`` map, generated from the real manifest.

        Cached per-instance (the manifest is a static bundled JSON file, not
        request-varying state) rather than hand-copied like the existing
        adapters' ``class_map``/``COMPONENT_CLASSES`` dicts.
        """
        if self._component_classes is None:
            manifest = self._fastblocks_ui().component_manifest()
            classes = {
                component["name"]: component["class_name"]
                for component in manifest["components"]
            }
            # State modifiers (`is-primary`, `is-large`, ...) are already the
            # real class token fastblocks-ui expects — pass them through
            # verbatim rather than translating, since there is nothing to
            # translate: fastblocks-ui's whole model is that template authors
            # write `ui-*`/`is-*` classes directly.
            for modifier in manifest["state_modifiers"]:
                classes.setdefault(modifier, modifier)
            self._component_classes = classes
        return self._component_classes

    def get_component_class(self, component: str) -> str:
        """Look up a component's real ``ui-*``/``is-*`` class from the manifest.

        Unlike Kelp/Web Awesome/Vanilla, there's no framework-specific prefix
        to translate to — an unrecognized name is returned unchanged (it's
        assumed to already be a valid ``ui-*``/``is-*`` token, matching how
        `fastblocks_ui`'s own helpers accept raw class strings).
        """
        if not component:
            return ""
        return self._classes().get(component, component)


def register_fastblocks_ui_functions(env: t.Any) -> None:
    """Register fastblocks-ui globals/filters on a live Jinja environment.

    Uses plain ``env.globals[name] = func`` / ``env.filters[name] = func``
    assignment — the real, working Jinja2 API (confirmed by reading both
    Jinja2's own ``Environment`` and this project's own ``init_envs()``,
    which populates ``templates.env.globals`` the same way). This
    deliberately does **not** copy ``register_kelp_functions``'s
    ``@env.global_(...)``/``@env.filter(...)`` decorator-call style: neither
    ``global_`` nor ``filter`` exists as a callable on a real Jinja2/
    ``AsyncJinja2Templates`` environment (confirmed by grepping every
    installed package under this project's own ``.venv`` — no such methods
    exist anywhere). Had ``register_kelp_functions`` ever actually been
    invoked with a real environment, it would have raised ``AttributeError``
    immediately — a second, independent bug beyond simply never being
    called. Worth its own follow-up in ``fastblocks`` (see WS-17's note on
    the pre-existing style adapters), out of scope to fix here.

    Constructs its own ``FastBlocksUIStyle`` instance rather than resolving
    "the active style" through the Oneiric resolver at call time: the
    pre-existing Kelp adapter's closures do a per-call
    ``resolve_instance(depends, "fastblocks", "styles")`` lookup. Rather than
    depend on an unverified resolver contract, this adapter
    is self-contained and correct on its own terms; the instance is *also*
    registered with the shared resolver below (best-effort, using the real
    ``Resolver.register(Candidate)`` method this project's own
    ``core/resolver.py`` and ``adapters/oneiric_helper.py`` actually expose)
    for other code that wants to resolve "the active style" generically.
    """
    style = FastBlocksUIStyle()
    fastblocks_ui = style._fastblocks_ui()

    globals_dict: dict[str, t.Any] = env.globals
    filters_dict: dict[str, t.Any] = env.filters

    globals_dict["fastblocks_ui_stylesheet_links"] = lambda: "\n".join(
        style.get_stylesheet_links()
    )
    globals_dict["fastblocks_ui_script_tags"] = lambda: "\n".join(
        style.get_script_tags()
    )
    filters_dict["fastblocks_ui_class"] = style.get_component_class

    # Delegate straight to the real, already-escaping fastblocks_ui helpers —
    # not a raw f-string reimplementation like kelp_component()/wa_button().
    #
    # Return the helper's `SafeHTML` UNCHANGED. Wrapping it in `str()` threw
    # away `__html__`, and `starlette_async_jinja` renders with
    # `autoescape=True`, so Jinja escaped the markup and the page displayed
    # literal `&lt;button ...&gt;` source text instead of a button. The helpers
    # already escape every interpolated value, so passing `SafeHTML` through is
    # both correct and safe -- it is exactly what fastblocks-htmy's adapter
    # does with the same functions.
    for helper_name in ("button", "card", "field", "alert", "container"):
        helper = getattr(fastblocks_ui, helper_name)
        globals_dict[f"ui_{helper_name}"] = lambda *a, __helper=helper, **kw: __helper(
            *a, **kw
        )

    with suppress(Exception):
        from ...core.resolver import get_resolver
        from ..oneiric_helper import register_candidate

        register_candidate(
            get_resolver(),
            domain="fastblocks",
            key="styles",
            factory=lambda: style,
            metadata={"style": "fastblocks_ui"},
        )


StyleSettings = FastBlocksUIStyleSettings
Style = FastBlocksUIStyle

__all__ = [
    "FastBlocksUIStyle",
    "FastBlocksUIStyleSettings",
    "Style",
    "StyleSettings",
    "register_fastblocks_ui_functions",
]
