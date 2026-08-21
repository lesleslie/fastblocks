"""Style adapter selection and Jinja wiring.

Establishes the runtime mechanism connecting ``config.app.style`` to a style
adapter's registered Jinja globals/filters. Two style values are supported:

- ``"vanilla"`` (explicit unstyled opt-out)
- ``"fastblocks_ui"`` (the default; provides ``ui_button``, ``ui_card``,
  stylesheet links, script tags, and class-name routing through the
  ``fastblocks-ui`` package)

Convention: a style named ``<name>`` (matching ``config.app.style``) may have
a Python adapter module at ``fastblocks.adapters.style.<name>``. If that
module defines a callable named ``register_<name>_functions``, it is invoked
once per template-environment build with the live Jinja environment. Styles
with no matching module, or no ``register_*_functions`` callable (e.g.
``vanilla``, which ships no Jinja globals today), are silently skipped — not
every style needs template-level wiring.

Note for anyone writing a new ``register_<name>_functions``: use plain
``env.globals[name] = func`` / ``env.filters[name] = func`` assignment — the
real, working Jinja2 API, and what ``fastblocks_ui.py``'s adapter does.
``@env.global_(...)`` / ``@env.filter(...)`` decorator calls do not exist on
a real ``Environment``/``AsyncJinja2Templates``; only ``env.globals[...] =``
and ``env.filters[...] =`` assignments do.

This is intentionally best-effort and non-raising: a missing/misconfigured
style adapter should never break template rendering for everyone else,
matching the defensive ``with suppress(Exception)`` convention used in
``StyleBase.__init__``.
"""

from __future__ import annotations

import typing as t
from importlib import import_module

from oneiric.core.logging import get_logger

_log = get_logger("fastblocks.style_registry")


def register_style_functions(env: t.Any, style_name: str | None) -> None:
    """Best-effort: wire the configured style's Jinja globals/filters into ``env``.

    Args:
        env: A Jinja ``Environment`` (or the ``AsyncJinja2Templates.env``
            FastBlocks actually builds).
        style_name: The configured style, typically ``config.app.style``
            (``"vanilla"`` or ``"fastblocks_ui"``). ``None`` or empty is a no-op.
    """
    if not style_name:
        return
    try:
        module = import_module(f"fastblocks.adapters.style.{style_name}")
    except ImportError:
        # No adapter module for this style at all -- expected/silent for
        # styles with no template-level wiring (e.g. "vanilla").
        return

    register_fn = getattr(module, f"register_{style_name}_functions", None)
    if not callable(register_fn):
        return

    try:
        register_fn(env)
    except Exception:  # noqa: BLE001, RUF100  # Framework-boundary invariant — never raise, regardless of style-adapter or logging-backend state.
        # A callable that exists but raises is logged rather than swallowed
        # silently so the failure mode is discoverable. This function's
        # hard invariant is "never raise, regardless of style-adapter or
        # logging-backend state"; logging itself swallows its own errors.
        try:
            _log.exception(
                f"register_{style_name}_functions(env) raised; style "
                f"{style_name!r} registered no Jinja globals/filters for "
                "this environment."
            )
        except Exception:  # noqa: BLE001, RUF100  # Last-resort: logging backend failure must not break template rendering.
            _log.warning(
                "style_registry logger.exception() failed; style "
                f"{style_name!r} failure is unauditable.",
            )


__all__ = ["register_style_functions"]
