"""FastBlocks HTMY components — integration adapter.

Adapted from the standalone ``fastblocks-htmy`` 0.5.0 PyPI package
(commit ``32ec2fabb...``, fetched 2026-08-21) into the
``fastblocks.adapters.templates.htmy_components`` namespace. Public surface
(5 functions) is carried over verbatim; the docstring's
``depends.resolve("fastblocks", "htmy")`` example is removed because the
caller is now inside fastblocks itself — the resolved adapter is
``fastblocks.adapters.templates.htmy.HTMYTemplates``.

FastBlocks templates use ``[[ ... ]]`` delimiters (not Jinja's ``{{ ... }}``).
This adapter exposes:

- the on-disk paths of the shipped ``fastblocks-ui`` CSS/JS bundle, so the app can
  mount them as a static route (resolved via ``importlib.resources``, no copy);
- cache-busted asset URLs keyed to the installed ``fastblocks-ui`` version, for apps
  that want the CSS served as a separate, browser-cacheable ``<link>``;
- ``inline_css()`` / ``inline_js()`` (and the ``fastblocks_ui_css_inline`` /
  ``fastblocks_ui_js_inline`` template globals), which embed the actual CSS/JS in
  ``<style>``/``<script type="module">`` tags instead -- the recommended default for
  htmx apps, since it avoids an extra request without needing a static mount at all.
  Both require the app's CSP (if any) to allow inline ``style-src``/``script-src``
  (a nonce or hash, or ``'unsafe-inline'``) -- if that's not an option, use the
  link/script-src URL globals below instead. ``enhance.js``'s own setup code is
  idempotent (custom-element registration checks ``customElements.get()`` first;
  auto-boot checks ``window.fastBlocksUI`` first), so re-inlining it more than once
  on the same page is a safe no-op, not a crash -- but it should still only need to
  appear once, in the base layout, the same as the CSS;
- a set of template globals (the htmy component classes plus the string helpers)
  to register once on the FastBlocks/Jinja environment, for the plain-Jinja-global
  usage path (``[[ ui_button(...) ]]`` — verified working, see
  ``tests/test_fastblocks_integration.py``); and
- ``trusted_components()`` / ``register_with_htmy_adapter()`` for the typed,
  ``render_component()``-mediated usage path (``[[ render_component("button", {...}) ]]``),
  which requires FastBlocks' htmy component registry to support pre-registered
  trusted components.

Example (FastBlocks/Starlette-style)::

    from fastblocks.adapters.templates.htmy_components import (
        asset_paths,
        template_globals,
        register_with_htmy_adapter,
    )

    app.mount(
        "/static/fastblocks-ui",
        StaticFiles(directory=asset_paths()["root"]),
        name="fastblocks-ui",
    )
    templates.env.globals.update(template_globals())

    # During app startup, once the FastBlocks htmy adapter is importable:
    from fastblocks.adapters.templates.htmy import HTMYTemplates

    await register_with_htmy_adapter(HTMYTemplates())

Then in a FastBlocks template's base layout (recommended -- inline, no extra request,
no static mount needed)::

    <head>
    [[ fastblocks_ui_css_inline ]]
    </head>
    [[ ui_button("Save", variant="primary") ]]
    [[ render_component("button", {"text": "Save", "variant": "primary"}) ]]
    [[ fastblocks_ui_js_inline ]]
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

import fastblocks_ui
from fastblocks_ui import SafeHTML

from . import (
    Alert,
    Breadcrumb,
    Burger,
    Button,
    Card,
    Checkbox,
    Column,
    Columns,
    Container,
    Dialog,
    Drawer,
    Dropdown,
    Field,
    Footer,
    Hero,
    Input,
    Level,
    Media,
    Navbar,
    NavGroups,
    NavList,
    Pagination,
    Progress,
    Section,
    Select,
    Shell,
    Switch,
    Table,
    Tabs,
    Tile,
    Title,
    ValidationSummary,
)


def trusted_components() -> dict[str, type]:
    """Typed htmy component classes shipped, keyed by name resolvable via FastBlocks' ``render_component()``.

    These are already-imported, already-vetted Python classes (this
    package's own installed code) — a different trust tier from arbitrary
    ``.py`` files an app author drops into a discovered-components
    directory. See ``fastblocks``'s
    ``AdvancedHTMYComponentRegistry.register_trusted_component`` for the
    full rationale.

    Keys match `fastblocks-ui`'s `manifest.json` component names (plus
    `validation_summary`, WS-16's manifest addition), so this dict's key set
    can be diffed against the manifest as a coverage check.
    """
    return {
        "alert": Alert,
        "breadcrumb": Breadcrumb,
        "button": Button,
        "card": Card,
        "checkbox": Checkbox,
        "column": Column,
        "columns": Columns,
        "container": Container,
        "dialog": Dialog,
        "field": Field,
        "footer": Footer,
        "hero": Hero,
        "input": Input,
        "level": Level,
        "media": Media,
        "burger": Burger,
        "drawer": Drawer,
        "dropdown": Dropdown,
        "nav_groups": NavGroups,
        "nav_list": NavList,
        "shell": Shell,
        "navbar": Navbar,
        "pagination": Pagination,
        "progress": Progress,
        "section": Section,
        "select": Select,
        "switch": Switch,
        "table": Table,
        "tabs": Tabs,
        "tile": Tile,
        "title": Title,
        "validation_summary": ValidationSummary,
    }


async def register_with_htmy_adapter(htmy_adapter: Any) -> None:
    """Register this package's typed components on a live FastBlocks htmy adapter instance.

    ``htmy_adapter`` is expected to expose an async
    ``register_trusted_components(dict[str, type])`` method, matching
    ``fastblocks.adapters.templates.htmy.HTMYTemplates``.
    """
    await htmy_adapter.register_trusted_components(trusted_components())


def asset_paths() -> dict[str, Path]:
    """Return on-disk paths of the shipped fastblocks-ui assets (static root + files)."""
    css = Path(fastblocks_ui.get_css_path())
    return {
        "root": Path(fastblocks_ui.get_static_path()),
        "css": css,
        "js": Path(fastblocks_ui.get_js_path()),
    }


def asset_urls(
    *, mount: str = "/static/fastblocks-ui", cache_bust: bool = True
) -> dict[str, str]:
    """Return cache-busted static URLs for the assets under ``mount``."""
    suffix = f"?v={fastblocks_ui.__version__}" if cache_bust else ""
    return {
        "css": f"{mount}/css/fastblocks-ui.css{suffix}",
        "js": f"{mount}/js/enhance.js{suffix}",
    }


def inline_css() -> SafeHTML:
    """Return the shipped fastblocks-ui CSS bundle wrapped in a ``<style>`` tag.

    Reads fresh from disk on every call (no caching here -- the app's own
    response/page cache is the right layer for that).

    Marked ``SafeHTML`` (implements ``__html__``) so it renders unescaped through
    a ``[[ ... ]]`` Jinja global the same way the typed htmy components already
    do -- see ``fastblocks_ui.helpers._render_fragment``. Reading the actual CSS
    on every call (instead of embedding a string literal at import time) means
    this can never drift from the installed fastblocks-ui version, the same
    property ``asset_paths()``/``asset_urls()`` already have.
    """
    css = Path(fastblocks_ui.get_css_path()).read_text(encoding="utf-8")
    return SafeHTML(f"<style>\n{css}\n</style>")


def inline_js() -> SafeHTML:
    """Return the shipped fastblocks-ui enhancement JS wrapped in a ``<script type="module">`` tag.

    Reads fresh from disk on every call -- same rationale as ``inline_css()``.

    Deliberately reads ``static/js/enhance.js`` directly rather than
    ``fastblocks_ui.get_js_path()`` (which points at ``fastblocks-ui.js``, a
    thin wrapper that re-exports from ``enhance.js`` via a *relative* ES
    import). That relative import only resolves when the wrapper is loaded
    as its own external file sitting next to ``enhance.js`` on disk -- inlined
    into an arbitrary page, ``./enhance.js`` would resolve against the page's
    own URL and 404 in virtually any real deployment. ``asset_urls()["js"]``
    already made the same choice, linking straight to ``enhance.js``.

    Safe to inline: ``enhance.js``'s setup code is idempotent by construction
    (custom-element registration checks ``customElements.get(name)`` before
    calling ``define()``; the auto-boot path checks ``window.fastBlocksUI``
    before running init), so if this ever ends up on the page more than once,
    re-running it is a harmless no-op rather than a thrown
    ``NotSupportedError`` or duplicate event listeners.
    """
    static_root = Path(fastblocks_ui.get_static_path())
    js = (static_root / "js" / "enhance.js").read_text(encoding="utf-8")
    return SafeHTML(f'<script type="module">\n{js}\n</script>')


def template_globals() -> dict[str, object]:
    """Globals to register on a FastBlocks/Jinja (``[[ ]]``) environment.

    Exposes both the typed htmy component classes and the zero-dependency string
    helpers (handy for quick fragments), plus ready-made asset URLs.
    """
    urls = asset_urls()
    return {
        # Typed htmy components
        "Alert": Alert,
        "Breadcrumb": Breadcrumb,
        "Button": Button,
        "Card": Card,
        "Checkbox": Checkbox,
        "Column": Column,
        "Columns": Columns,
        "Container": Container,
        "Dialog": Dialog,
        "Field": Field,
        "Footer": Footer,
        "Hero": Hero,
        "Input": Input,
        "Level": Level,
        "Media": Media,
        "Burger": Burger,
        "Drawer": Drawer,
        "Dropdown": Dropdown,
        "NavGroups": NavGroups,
        "NavList": NavList,
        "Shell": Shell,
        "Navbar": Navbar,
        "Pagination": Pagination,
        "Progress": Progress,
        "Section": Section,
        "Select": Select,
        "Switch": Switch,
        "Table": Table,
        "Tabs": Tabs,
        "Tile": Tile,
        "Title": Title,
        "ValidationSummary": ValidationSummary,
        # String helpers for quick fragments
        "ui_button": fastblocks_ui.button,
        "ui_card": fastblocks_ui.card,
        "ui_field": fastblocks_ui.field,
        "ui_alert": fastblocks_ui.alert,
        # Asset URLs (link/script-src-based, browser-cacheable -- see inline_css()/
        # inline_js() for the recommended alternative)
        "fastblocks_ui_css": urls["css"],
        "fastblocks_ui_js": urls["js"],
        # Inline CSS/JS (recommended default -- see module docstring)
        "fastblocks_ui_css_inline": inline_css(),
        "fastblocks_ui_js_inline": inline_js(),
    }
