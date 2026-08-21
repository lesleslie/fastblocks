"""FastBlocks style adapters.

Two style values are supported by ``config.app.style``:

- ``"vanilla"`` — explicit unstyled opt-out; no Jinja globals/filters wired.
- ``"fastblocks_ui"`` (default) — provides CSS/JS asset paths and class
  lookups via the ``fastblocks-ui`` package; see
  ``fastblocks/adapters/style/fastblocks_ui.py``.

The future ``renderer`` axis (``jinja2`` | ``htmy``) is documented as the
unifying abstraction in ``fastblocks/core/style_registry.py``'s docstring.
"""
