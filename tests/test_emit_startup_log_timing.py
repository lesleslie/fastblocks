"""Phase 1.5.x remediation Card 10 — emit_startup_log timing.

F-L5-04 (Phase 1.5 adversarial review): ``emit_startup_log`` was
fired AFTER ``await _get_app_instance()`` returned inside
``get_app()``. By the time the log line appeared, the Starlette
app was already accepting requests. Operators reacting to
``too_many_shadowed`` or ``0 candidates registered`` had no
chance to fail-fast before app construction completed.

The Card 10 fix introduces an EARLIER emit inside
``_handle_registration()`` — BEFORE ``_get_app_instance()``.
The pre-app emit shows operators the bootstrap state (post
``register_builtin_adapters``, pre app construction); the
existing post-app emit continues as the final observability
point. Both emits use the same module-level facade so the
counter is not inflated (Card 3 contract).

This test pins the order:

  1. ``_handle_registration`` calls ``emit_startup_log`` exactly
     once (the pre-app snapshot).
  2. ``get_app()`` calls ``emit_startup_log`` exactly once more
     (the post-app snapshot — preserves Card 6 invariants).
  3. ``_handle_registration`` runs BEFORE ``_get_app_instance``,
     so any operator-visible signal fires before the app is
     constructed.

See ``docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md``
Phase 1.5x remediation, Card 10 (F-L5-04).
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from fastblocks import main


@pytest.fixture
def reset_main_globals() -> Any:
    """Reset module-level cache so each test starts clean."""
    saved_app = main._app_instance
    saved_logger = main._logger_instance
    main._app_instance = None
    main._logger_instance = None
    try:
        yield
    finally:
        main._app_instance = saved_app
        main._logger_instance = saved_logger


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_registration_emits_startup_log(
    reset_main_globals: Any,
) -> None:
    """``_handle_registration`` calls ``emit_startup_log`` exactly once.

    The pre-app emit is the Card 10 fix — operators see the
    bootstrap state BEFORE the app is constructed. Without this,
    the F-L5-04 timing problem persists silently.
    """
    mock_app = mock.MagicMock()

    async def mock_get_app_dependency(name: str) -> Any:
        return mock_app

    with (
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch(
            "oneiric.adapters.bootstrap.register_builtin_adapters"
        ),
        mock.patch.object(main, "_handle_adapter_registration"),
        mock.patch.object(main, "_get_dependency", side_effect=mock_get_app_dependency),
        mock.patch.object(
            main, "_get_logger_instance", return_value=mock.MagicMock()
        ),
        mock.patch(
            "fastblocks.core.resolver_metrics.emit_startup_log"
        ) as emit_spy,
    ):
        await main._handle_registration()

    assert emit_spy.call_count == 1, (
        f"_handle_registration must call emit_startup_log exactly once; "
        f"saw {emit_spy.call_count} calls. Card 10 pre-app emit is missing."
    )
    facade = emit_spy.call_args.args[0]
    assert facade is main._resolver, (
        "Pre-app emit passed a different facade than the module "
        "level _resolver — Card 3 contract broken."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_app_emits_startup_log_twice_total(
    reset_main_globals: Any,
) -> None:
    """``get_app()`` ends with two emits (pre-app + post-app).

    Card 10 adds an emit to ``_handle_registration``. Card 6
    pins the existing post-app emit in ``get_app``. The two
    coexist; total observed emits across one get_app() call = 2.
    """
    mock_app = mock.MagicMock()

    async def mock_get_app_dependency(name: str) -> Any:
        return mock_app

    with (
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch(
            "oneiric.adapters.bootstrap.register_builtin_adapters"
        ),
        mock.patch.object(main, "_handle_adapter_registration"),
        mock.patch.object(main, "_get_dependency", side_effect=mock_get_app_dependency),
        mock.patch.object(
            main, "_get_logger_instance", return_value=mock.MagicMock()
        ),
        mock.patch(
            "fastblocks.core.resolver_metrics.emit_startup_log"
        ) as emit_spy,
    ):
        await main.get_app()

    assert emit_spy.call_count == 2, (
        f"get_app() should now trigger 2 emit_startup_log calls "
        f"(one in _handle_registration, one at end of get_app). "
        f"Saw {emit_spy.call_count}. Either Card 10 pre-app emit "
        "is missing or the post-app emit in get_app was removed."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_handle_registration_runs_before_get_app_instance(
    reset_main_globals: Any,
) -> None:
    """``_handle_registration`` runs BEFORE ``_get_app_instance``.

    The Card 10 fix depends on the pre-app emit firing before the
    app is constructed. The orchestration order in ``get_app``
    pins this: ``_handle_registration`` first, then
    ``_get_app_instance``. A future contributor who reverses
    these would silently undo Card 10.
    """
    calls: list[str] = []

    async def tracking_handler() -> None:
        calls.append("handle_registration")

    async def tracking_instance() -> Any:
        calls.append("get_app_instance")
        return mock.MagicMock()

    with (
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch.object(main, "_handle_registration", new=tracking_handler),
        mock.patch.object(main, "_handle_adapter_registration"),
        mock.patch.object(main, "_get_app_instance", new=tracking_instance),
        mock.patch.object(
            main, "_get_logger_instance", return_value=mock.MagicMock()
        ),
        mock.patch(
            "fastblocks.core.resolver_metrics.emit_startup_log"
        ),
    ):
        await main.get_app()

    assert calls == ["handle_registration", "get_app_instance"], (
        f"Orchestration order changed: {calls!r}. "
        "_handle_registration must run before _get_app_instance "
        "so the pre-app startup_log fires before the Starlette "
        "app is constructed."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_pre_app_emit_uses_module_facade(
    reset_main_globals: Any,
) -> None:
    """The pre-app emit MUST use ``main._resolver`` (Card 3 contract)."""
    mock_app = mock.MagicMock()

    async def mock_get_app_dependency(name: str) -> Any:
        return mock_app

    with (
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch(
            "oneiric.adapters.bootstrap.register_builtin_adapters"
        ),
        mock.patch.object(main, "_handle_adapter_registration"),
        mock.patch.object(main, "_get_dependency", side_effect=mock_get_app_dependency),
        mock.patch.object(
            main, "_get_logger_instance", return_value=mock.MagicMock()
        ),
        mock.patch(
            "fastblocks.core.resolver_metrics.emit_startup_log"
        ) as emit_spy,
    ):
        await main._handle_registration()

    facade = emit_spy.call_args.args[0]
    assert facade is main._resolver, (
        "_handle_registration must pass the module-level facade "
        "to emit_startup_log. Card 3 contract: facade is required "
        "to keep registry_size_total invariant intact."
    )
