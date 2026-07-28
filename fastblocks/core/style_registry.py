"""Style adapter selection and Jinja wiring.

Establishes the runtime mechanism connecting ``config.app.style`` to a style
adapter's registered Jinja globals/filters — a mechanism that, before this
module existed, was assumed present but never actually invoked anywhere.
A direct grep across the framework confirmed ``register_kelp_functions``
(``fastblocks/adapters/style/kelp.py``) and ``register_webawesome_functions``
(``fastblocks/adapters/style/webawesome.py``) had zero call sites outside
their own module and ``__all__`` — nothing in ``jinja2.py`` ever invoked them
based on ``config.app.style`` or any other selection signal. This module is
that missing wiring (see ``fastblocks-ui``'s cross-repo remediation plan,
WS-17).

Convention: a style named ``<name>`` (matching ``config.app.style``, e.g.
``"vanilla"``, ``"kelp"``, ``"webawesome"``, ``"fastblocks_ui"``) may have a
Python adapter module at ``fastblocks.adapters.style.<name>``. If that module
defines a callable named ``register_<name>_functions`` — the naming
convention the three pre-existing adapters already (partially) follow — it
is invoked once per template-environment build with the live Jinja
environment. Styles with no matching module, or no
``register_*_functions`` callable (e.g. ``vanilla``, which ships no Jinja
globals today), are silently skipped — not every style needs template-level
wiring.

Note for anyone writing a new ``register_<name>_functions``: use plain
``env.globals[name] = func`` / ``env.filters[name] = func`` assignment — the
real, working Jinja2 API, and what ``fastblocks_ui.py``'s adapter does.
``kelp.py``/``webawesome.py``'s existing ``register_*_functions`` instead
call ``@env.global_(...)``/``@env.filter(...)`` as if they were decorator
methods on ``env`` — no such methods exist on a real Jinja2/
``AsyncJinja2Templates`` environment (confirmed by grepping every installed
package in this project's own ``.venv``), so those two would raise
``AttributeError`` immediately if ever actually invoked. That failure is
swallowed rather than breaking template rendering, but it also means
selecting ``style = "kelp"`` or ``style = "webawesome"`` silently registers
nothing — a second, independent bug in those adapters beyond simply never
being called, worth its own follow-up in ``fastblocks`` (out of scope here).
Unlike an unmatched/missing style module (a normal, silent no-op), a
``register_<name>_functions`` that exists but raises is logged (via
``oneiric.core.logging.get_logger("fastblocks.style_registry")``) before
being swallowed, so this specific failure mode is at least discoverable —
not invisible the way it was before this module existed.

This is intentionally best-effort and non-raising: a missing/misconfigured
style adapter should never break template rendering for everyone else,
matching the defensive ``with suppress(Exception)`` convention already used
throughout ``fastblocks/adapters/style/*.py`` and ``StyleBase.__init__``.
"""

from __future__ import annotations

import typing as t
from contextlib import suppress
from importlib import import_module


def register_style_functions(env: t.Any, style_name: str | None) -> None:
    """Best-effort: wire the configured style's Jinja globals/filters into ``env``.

    Args:
        env: A Jinja ``Environment`` (or the ``AsyncJinja2Templates.env``
            FastBlocks actually builds) exposing ``global_``/``filter``
            registration, as ``register_kelp_functions`` and friends expect.
        style_name: The configured style, typically ``config.app.style``
            (e.g. ``"vanilla"``, ``"kelp"``, ``"fastblocks_ui"``). ``None``
            or empty is a no-op.
    """
    if not style_name:
        return
    try:
        module = import_module(f"fastblocks.adapters.style.{style_name}")
    except Exception:
        # No adapter module for this style at all -- expected/silent for
        # styles with no template-level wiring (e.g. "vanilla").
        return

    register_fn = getattr(module, f"register_{style_name}_functions", None)
    if not callable(register_fn):
        return

    try:
        register_fn(env)
    except Exception:
        # Unlike a missing module (above), a callable that exists but raises
        # is exactly the failure mode this module's docstring warns about
        # (kelp.py/webawesome.py's register_*_functions would raise
        # AttributeError immediately if ever invoked, since they call
        # nonexistent env.global_()/env.filter() methods). Swallowing it
        # silently here would repeat the original problem this workstream
        # exists to fix -- log it so the bug is at least discoverable,
        # rather than invisible the way it was before. Logging itself is
        # wrapped too: this function's hard invariant is "never raise,
        # regardless of style-adapter or logging-backend state."
        with suppress(Exception):
            from oneiric.core.logging import get_logger

            get_logger("fastblocks.style_registry").exception(
                f"register_{style_name}_functions(env) raised; style "
                f"{style_name!r} registered no Jinja globals/filters for "
                "this environment."
            )


__all__ = ["register_style_functions"]
