"""Focused contracts for FastBlocks integration modules.

These tests pin the explicit failure semantics added in Task 1: the
sanitizer must fail closed (never return the unsafe input), event
``publish`` must report a failed subscriber, registration must not lie
about success, and workflow/health result objects must surface
unsupported steps and per-component errors.
"""

from __future__ import annotations

import pytest


# ---------------------------------------------------------------------------
# Step 3 — sanitizer fail-closed contract
# ---------------------------------------------------------------------------


def test_sanitizer_failure_rejects_input(monkeypatch: pytest.MonkeyPatch) -> None:
    """A broken sanitizer must NOT return the original untrusted value.

    The fail-open catch in ``_sanitize_context_value`` previously returned
    the raw input, leaving the dangerous payload in the template context.
    The fix returns an empty string surface (closed) and records an
    error so downstream validation can refuse to render.
    """
    from fastblocks._validation_integration import get_validation_service

    service = get_validation_service()
    assert service._sanitizer is not None

    def broken_sanitizer(_value: str) -> str:
        raise RuntimeError("sanitizer down")

    monkeypatch.setattr(service._sanitizer, "sanitize_html", broken_sanitizer)
    errors: list[str] = []
    value = "<script>alert(1)</script>"

    sanitized = service._sanitize_context_value("body", value, errors)

    assert sanitized != value
    assert errors and "Failed to sanitize body" in errors[0]


# ---------------------------------------------------------------------------
# Step 6 — event delivery honesty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_publish_reports_failed_subscriber() -> None:
    """A failing subscriber must mark the publish result False."""
    from fastblocks._events_integration import (
        Event,
        EventPriority,
        EventPublisher,
        EventSubscription,
    )

    class BrokenHandler:
        async def handle(self, _event: Event) -> None:
            raise RuntimeError("subscriber failed")

    publisher = EventPublisher()
    await publisher.subscribe(EventSubscription("demo", BrokenHandler()))
    result = await publisher.publish(
        Event("demo", "test", {}, EventPriority.NORMAL)
    )

    assert result is False


@pytest.mark.asyncio
async def test_subscribe_returns_false_on_failure() -> None:
    """A failed subscription must NOT return True."""
    from fastblocks._events_integration import EventPublisher, EventSubscription

    publisher = EventPublisher()

    class BadHandler:
        pass

    # Replace the subscriptions dict itself with a stub that raises on the
    # only call ``subscribe`` uses to mutate state.  ``setdefault`` in CPython
    # does not dispatch through ``__setitem__`` for dict subclasses, so we
    # must patch the bucket directly.
    sub = EventSubscription("demo", BadHandler())

    # Inject a corrupted bucket that raises on append.
    def _raising_append(_item: object) -> None:
        raise RuntimeError("store failed")

    publisher.subscriptions = {"demo": type("BoomList", (), {"append": staticmethod(_raising_append)})()}  # type: ignore[assignment]

    result = await publisher.subscribe(sub)
    assert result is False


@pytest.mark.asyncio
async def test_subscribe_returns_true_on_success() -> None:
    """A successful subscription must return True and the handler is stored."""
    from fastblocks._events_integration import EventPublisher, EventSubscription

    publisher = EventPublisher()

    class OkHandler:
        async def handle(self, _event: object) -> None:
            return None

    result = await publisher.subscribe(EventSubscription("ok", OkHandler()))
    assert result is True
    assert "ok" in publisher.subscriptions
    assert publisher.subscriptions["ok"]


# ---------------------------------------------------------------------------
# Step 7 — workflow honesty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_unsupported_workflow_step_is_recorded_as_failed() -> None:
    """A step whose action has no handler must be recorded as failed."""
    from fastblocks._workflows_integration import (
        BasicWorkflowEngine,
        WorkflowDefinition,
        WorkflowStep,
        WorkflowState,
    )

    engine = BasicWorkflowEngine()

    workflow = WorkflowDefinition(
        workflow_id="probe",
        name="probe",
        description="probe",
        steps=[
            WorkflowStep(
                step_id="not_impl",
                name="Unsupported",
                action="unsupported_action",
                params={},
            )
        ],
        max_execution_time=10,
    )

    async def _ok(_ctx: dict, _params: dict) -> dict:
        return {"ok": True}

    # Registered handler is for a different action — the step's action has
    # no handler.
    result = await engine.execute(
        workflow,
        context={},
        action_handlers={"known_action": _ok},
    )

    # Engine reports the step as failed because no handler is registered.
    assert "not_impl" in result.step_results
    assert result.step_results["not_impl"]["state"] == "failed"
    assert result.state == WorkflowState.FAILED


@pytest.mark.asyncio
async def test_workflow_step_exception_is_recorded_in_state() -> None:
    """A handler that raises must set the step state to failed with error."""
    from fastblocks._workflows_integration import (
        BasicWorkflowEngine,
        WorkflowDefinition,
        WorkflowStep,
        WorkflowState,
    )

    engine = BasicWorkflowEngine()

    workflow = WorkflowDefinition(
        workflow_id="boom",
        name="boom",
        description="boom",
        steps=[
            WorkflowStep(
                step_id="explodes",
                name="Explodes",
                action="explode",
                params={},
            )
        ],
        max_execution_time=10,
    )

    async def _boom(_ctx: dict, _params: dict) -> dict:
        raise RuntimeError("kaboom")

    result = await engine.execute(
        workflow,
        context={},
        action_handlers={"explode": _boom},
    )

    assert result.step_results["explodes"]["state"] == "failed"
    assert "kaboom" in result.step_results["explodes"]["error"]
    assert result.state == WorkflowState.FAILED


# ---------------------------------------------------------------------------
# Step 7 — health honesty
# ---------------------------------------------------------------------------


@pytest.mark.asyncio
async def test_health_summary_preserves_successful_component_status() -> None:
    """A failing one component must not erase healthy sibling status."""
    from fastblocks._health_integration import (
        HealthCheckResult,
        HealthService,
        HealthStatus,
        _determine_overall_health_status,
        _get_component_health_results,
    )

    service = HealthService()

    class GoodCheck:
        component_id = "templates"
        component_name = "Good"

        async def _perform_health_check(self, _check_type: object) -> object:
            return HealthCheckResult(
                component_id="templates",
                component_name="Good",
                status=HealthStatus.HEALTHY,
                check_type="standard",
                message="ok",
            )

    class BadCheck:
        component_id = "cache"
        component_name = "Bad"

        async def _perform_health_check(self, _check_type: object) -> object:
            raise RuntimeError("explode")

    await service.register_component(GoodCheck())
    await service.register_component(BadCheck())

    results = await _get_component_health_results(service)

    # Healthy sibling is preserved.
    assert "templates" in results
    assert results["templates"]["status"] == HealthStatus.HEALTHY
    # Failing component surfaces the error without erasing the healthy one.
    assert "cache" in results
    assert results["cache"]["status"] == "unknown"
    assert "error" in results["cache"]["details"]

    # Overall status reflects the healthy component despite the failure.
    overall = _determine_overall_health_status(results)
    assert overall in {HealthStatus.HEALTHY, HealthStatus.UNKNOWN}
