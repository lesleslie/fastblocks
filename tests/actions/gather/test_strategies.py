"""Tests for the gather strategy domain exceptions and failure paths.

Covers Task 2 Step 2: replace bare ``raise Exception(msg)`` in
``fastblocks/actions/gather/strategies.py`` (raised on
``COLLECT_ERRORS`` failure) with a FastBlocks domain exception
(``GatherError``) and chain the cause.
"""

from __future__ import annotations

from typing import Any

import pytest

from fastblocks.actions.gather.strategies import (
    ErrorStrategy,
    GatherStrategy,
    gather_with_strategy,
)
from fastblocks.exceptions import GatherError


async def test_collect_errors_raises_gather_error_with_cause() -> None:
    """Collect-errors strategy must raise ``GatherError`` chained to the original cause."""
    strategy = GatherStrategy(
        error_strategy=ErrorStrategy.COLLECT_ERRORS,
        retry_attempts=0,
    )

    with pytest.raises(GatherError) as excinfo:
        await gather_with_strategy(
            [_failing_task("underlying-cause")],
            strategy,
        )

    assert excinfo.value.__cause__ is not None
    assert isinstance(excinfo.value.__cause__, RuntimeError)
    assert "underlying-cause" in str(excinfo.value.__cause__)
    assert excinfo.value.errors, "GatherError should retain the original errors"


async def test_collect_errors_with_no_failures_does_not_raise() -> None:
    """Collect-errors strategy should not raise when at least one task succeeds."""
    strategy = GatherStrategy(
        error_strategy=ErrorStrategy.COLLECT_ERRORS,
        retry_attempts=0,
    )

    async def _ok_task() -> str:
        return "ok"

    result = await gather_with_strategy(
        [_ok_task(), _failing_task("ignored")],
        strategy,
    )

    assert result.is_success is True
    assert result.errors  # at least one error recorded, but not raised


async def test_fail_fast_reraises_original_exception() -> None:
    """Fail-fast strategy must re-raise the original error directly."""
    strategy = GatherStrategy(
        error_strategy=ErrorStrategy.FAIL_FAST,
        retry_attempts=0,
    )

    with pytest.raises(RuntimeError, match="boom"):
        await gather_with_strategy(
            [_failing_task("boom")],
            strategy,
        )


async def _failing_task(message: str = "boom") -> Any:
    raise RuntimeError(message)
