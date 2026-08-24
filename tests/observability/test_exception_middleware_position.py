from __future__ import annotations

# Note: ExceptionMiddleware is from Starlette, NOT re-exported by fastblocks.applications
from starlette.middleware.exceptions import ExceptionMiddleware

from fastblocks.applications import FastBlocks, MiddlewareManager


def test_outermost_default_via_middleware_manager_dict():
    """Per Δ45: Commit 0c ordering tests target MiddlewareManager.get_middleware_stack()
    dict shape (applications.py:114-124), not FastBlocks.get_middleware_stack()
    list-of-tuples shape."""
    app = FastBlocks()
    stack = app.middleware_manager.get_middleware_stack()
    assert isinstance(stack, dict)
    assert isinstance(stack["user_middleware"], list)
    assert isinstance(stack["system_middleware"], dict)
    # ExceptionMiddleware is at system_middleware[OUTERMOST] position by default
    assert stack["system_middleware"]["OUTERMOST"]["class"] == "ExceptionMiddleware"


def test_innermost_opt_out_removes_exception_middleware():
    app = FastBlocks()
    # Default: ExceptionMiddleware is in system_middleware
    stack_before = app.middleware_manager.get_middleware_stack()
    assert "ExceptionMiddleware" in {m["class"] for m in stack_before["system_middleware"].values()}
    # Opt out via register_user_exception_middleware(app, position="innermost")
    from fastblocks.applications import register_user_exception_middleware

    register_user_exception_middleware(app, position="innermost")
    stack_after = app.middleware_manager.get_middleware_stack()
    # After opt-out: ExceptionMiddleware now at INNERMOST position
    assert stack_after["system_middleware"]["INNERMOST"]["class"] == "ExceptionMiddleware"


def test_position_enum_supports_outermost_and_innermost_simultaneously():
    """The ``MiddlewarePosition`` enum allows BOTH ``OUTERMOST`` and
    ``INNERMOST`` registrations to coexist in ``system_middleware`` at the
    same time — required for the Commit 11 OtelMiddleware scenario where
    one middleware lives at each boundary position simultaneously.

    Registers ``ExceptionMiddleware`` at OUTERMOST (default) and a sentinel
    placeholder at INNERMOST, then asserts the dict reflects both.
    """
    from fastblocks.applications import register_user_exception_middleware
    from fastblocks.middleware import MiddlewarePosition

    app = FastBlocks()

    # Default: ExceptionMiddleware lands at OUTERMOST.
    register_user_exception_middleware(app, position="outermost")

    # Register a sentinel at INNERMOST to simulate OtelMiddleware at the
    # other boundary (Commit 11 will register the real OtelMiddleware here).
    class _OtelSentinelMiddleware:
        pass

    app.add_system_middleware(
        _OtelSentinelMiddleware, position=MiddlewarePosition.INNERMOST
    )

    stack = app.middleware_manager.get_middleware_stack()

    # Both boundary positions are present simultaneously in the dict.
    assert "OUTERMOST" in stack["system_middleware"]
    assert "INNERMOST" in stack["system_middleware"]
    # OUTERMOST holds ExceptionMiddleware; INNERMOST holds the sentinel.
    assert stack["system_middleware"]["OUTERMOST"]["class"] == "ExceptionMiddleware"
    assert (
        stack["system_middleware"]["INNERMOST"]["class"]
        == "_OtelSentinelMiddleware"
    )


def test_middleware_position_enum_has_boundary_positions():
    """Verify MiddlewarePosition has OUTERMOST = -1 and INNERMOST = 99.

    OUTERMOST sorts BEFORE all named positions (numeric value -1);
    INNERMOST sorts AFTER all named positions (numeric value 99).
    """
    from fastblocks.middleware import MiddlewarePosition

    assert MiddlewarePosition.OUTERMOST.value == -1
    assert MiddlewarePosition.INNERMOST.value == 99
    # OUTERMOST sorts before all named positions
    assert MiddlewarePosition.OUTERMOST.value < MiddlewarePosition.CSRF.value
    # INNERMOST sorts after all named positions
    assert MiddlewarePosition.INNERMOST.value > MiddlewarePosition.SECURITY_HEADERS.value
