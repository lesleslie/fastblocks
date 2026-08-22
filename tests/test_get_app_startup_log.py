"""Phase 1.5.x remediation Card 6 — get_app() startup-log end-to-end pin.

F-L4-05 (Phase 1.5 adversarial review): no test exercises the
``emit_startup_log`` line inside ``get_app()``. Phase 6 will replace
the log line with a Prometheus exporter over the same counter, so
the contract below must hold end-to-end before the migration ships.

This test:

  * Drives ``get_app()`` past every internal helper (dev-mode
    check, registration, adapter-metadata registration) without
    actually importing the Oneiric ``bootstrap`` symbols — same
    mocking posture as ``tests/test_main_comprehensive.py``.
  * Asserts ``emit_startup_log`` is invoked exactly once, with the
    module-level facade (``main._resolver``) so the counter is not
    inflated (Card 3 contract).
  * Verifies the log line emitted matches the master plan format
    ``Oneiric resolver: 1 registry, N candidates, M shadowed``.
  * Asserts the app returned is the cached singleton on the second
    call (no re-registration).

Per-session module globals (``main._app_instance``,
``main._logger_instance``) are reset to ``None`` in fixture
teardown so other tests do not inherit a stale cache.

See ``docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md``
Phase 1.5x remediation, Card 6 (F-L4-05).
"""

from __future__ import annotations

from typing import Any
from unittest import mock

import pytest
from fastblocks import main
from fastblocks.core.resolver import FastblocksRegistry


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
async def test_get_app_emits_startup_log_with_module_facade(
    reset_main_globals: Any,
) -> None:
    """get_app() must call emit_startup_log exactly once with the module facade.

    Card 3 fix (F-L1-01) made the facade parameter required on
    emit_startup_log so the counter cannot be inflated by an
    auto-constructed facade. The natural caller is the module-level
    ``main._resolver`` — capturing it here pins both behaviors.
    """
    mock_app = mock.MagicMock(name="mock-app")
    mock_logger = mock.MagicMock(name="mock-logger")

    async def mock_get_app_dependency(name: str) -> Any:
        if name == "app":
            return mock_app
        if name == "logger":
            return mock_logger
        raise RuntimeError(f"No dependency: {name}")

    with (
        mock.patch.object(main, "_dependency", create=True, new=mock_get_app_dependency),
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch.object(main, "_handle_registration"),
        mock.patch.object(main, "_handle_adapter_registration"),
        mock.patch.object(main, "_get_dependency", side_effect=mock_get_app_dependency),
        mock.patch.object(
            main, "_get_logger_instance", return_value=mock_logger
        ),
        mock.patch(
            "fastblocks.core.resolver_metrics.emit_startup_log"
        ) as emit_spy,
    ):
        app = await main.get_app()

    assert app is mock_app
    assert main._app_instance is mock_app
    emit_spy.assert_called_once()
    call_args = emit_spy.call_args
    # emit_startup_log takes (facade, *, domains=...) — Card 3 made facade required.
    assert len(call_args.args) >= 1 or "facade" in call_args.kwargs
    facade_arg = (
        call_args.args[0]
        if call_args.args
        else call_args.kwargs["facade"]
    )
    assert facade_arg is main._resolver, (
        "startup_log was called with a different facade than the "
        "module-level _resolver. Card 3 fix required the facade; "
        "auto-constructing a second one would re-introduce the "
        "counter inflation bug."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_app_does_not_emit_startup_log_on_cached_call(
    reset_main_globals: Any,
) -> None:
    """A cached get_app() must not re-emit the startup log line.

    The check inside get_app() (``if _app_instance is None``)
    must remain the only emit trigger. A future contributor who
    moves emit_startup_log out of that guard would double-emit
    on every subsequent call.
    """
    mock_app = mock.MagicMock(name="mock-app-cached")

    async def mock_get_app_dependency(name: str) -> Any:
        if name == "app":
            return mock_app
        return mock.MagicMock()

    # Prime the cache.
    main._app_instance = None
    with (
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch.object(main, "_handle_registration"),
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
        # Second call uses cached instance.
        await main.get_app()
        await main.get_app()

    # Startup log must fire exactly once even across three get_app calls.
    assert emit_spy.call_count == 1, (
        f"emit_startup_log fired {emit_spy.call_count} times across "
        "three get_app() calls; the cache guard did not prevent re-emit."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_app_startup_log_passed_correct_facade_type(
    reset_main_globals: Any,
) -> None:
    """The facade passed to emit_startup_log must be a FastblocksRegistry, not a raw Resolver.

    Card 3 contract: facade must be a FastblocksRegistry so the
    metrics emit follows the consolidated singleton. A raw
    ``oneiric.core.resolution.Resolver`` would bypass the
    registry_size_total invariant.
    """
    mock_app = mock.MagicMock()

    async def mock_get_app_dependency(name: str) -> Any:
        return mock_app

    with (
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch.object(main, "_handle_registration"),
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

    facade = emit_spy.call_args.args[0]
    assert isinstance(facade, FastblocksRegistry), (
        f"get_app() passed {type(facade).__name__} to emit_startup_log; "
        "must be a FastblocksRegistry to keep the consolidation "
        "invariant (ADR 0008 Rule 2)."
    )


@pytest.mark.unit
@pytest.mark.asyncio
async def test_get_app_emits_log_with_expected_format(
    reset_main_globals: Any,
    capsys: pytest.CaptureFixture[str],
) -> None:
    """The startup log line must include the prefix + 3 counters.

    The string format is captured by the master plan (line 288) as
    the operator-facing surface until Phase 6 replaces it with a
    Prometheus exporter. Pinning the prefix here means a
    reformatting regression surfaces in CI, not at 2am when an
    operator is grepping for the line.

    The numeric value of ``registry_size_total`` accumulates across
    pytest sessions (one bump per FastblocksRegistry construction)
    so we assert structural invariants only: the prefix, and a
    counter triple ``<n> registry, <n> candidates, <n> shadowed``.
    The actual values are exercised by tests/core/test_resolver_metrics.py.

    Note: emit_startup_log uses Oneiric's structured logger
    (``fastblocks.resolver_metrics``), which writes through to
    stdout rather than propagating via stdlib logging. We use
    ``capsys`` to capture it (caplog cannot, by design).
    """
    import re

    mock_app = mock.MagicMock()

    async def mock_get_app_dependency(name: str) -> Any:
        return mock_app

    with (
        mock.patch.object(main, "_check_dev_mode"),
        mock.patch.object(main, "_handle_registration"),
        mock.patch.object(main, "_handle_adapter_registration"),
        mock.patch.object(main, "_get_dependency", side_effect=mock_get_app_dependency),
        mock.patch.object(
            main, "_get_logger_instance", return_value=mock.MagicMock()
        ),
    ):
        await main.get_app()

    captured = capsys.readouterr()
    log_text = captured.out + captured.err
    matching = re.findall(
        r"Oneiric resolver: \d+ registry, \d+ candidates, \d+ shadowed",
        log_text,
    )
    assert matching, (
        "No log line matched the documented counter-triple format "
        f"under the 'Oneiric resolver:' prefix. Captured:\n{log_text[:2000]}"
    )
