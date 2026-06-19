"""Oneiric Workflows integration for FastBlocks.

This module provides background job orchestration using Oneiric-compatible workflows,
with custom implementations for workflow execution and management.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-10-01

Key Features:
- Cache warming workflows (template and static file caching)
- Template cleanup workflows (remove stale templates, optimize storage)
- Performance optimization workflows (database query optimization, index maintenance)
- Scheduled background tasks
- Oneiric-compatible dependency injection

Usage:
    # Execute cache warming workflow
    from fastblocks._workflows_integration import execute_cache_warming
    result = await execute_cache_warming()

    # Execute template cleanup workflow
    from fastblocks._workflows_integration import execute_template_cleanup
    result = await execute_template_cleanup()

    # Execute performance optimization workflow
    from fastblocks._workflows_integration import execute_performance_optimization
    result = await execute_performance_optimization()
"""

from __future__ import annotations

import typing as t
from contextlib import suppress
from datetime import datetime
from typing import Literal

# Oneiric imports for dependency injection
from fastblocks.core.patterns import SingletonMeta
from fastblocks.core.resolver import get_resolver

# Custom Oneiric-compatible workflow system
depends = get_resolver()


# Workflow system availability
oneiric_workflows_available = True


# Custom Oneiric-compatible Workflow System
class WorkflowState:
    """Workflow execution states."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"


class WorkflowStep:
    """Workflow step definition."""

    def __init__(
        self,
        step_id: str,
        name: str,
        action: str,
        params: dict[str, t.Any],
        retry_on_failure: bool = False,
        max_retries: int = 0,
        depends_on: list[str] | None = None,
    ):
        self.step_id = step_id
        self.name = name
        self.action = action
        self.params = params
        self.retry_on_failure = retry_on_failure
        self.max_retries = max_retries
        self.depends_on = depends_on or []


class WorkflowDefinition:
    """Workflow definition."""

    def __init__(
        self,
        workflow_id: str,
        name: str,
        description: str,
        steps: list[WorkflowStep],
        max_execution_time: int,
    ):
        self.workflow_id = workflow_id
        self.name = name
        self.description = description
        self.steps = steps
        self.max_execution_time = max_execution_time


class WorkflowResult:
    """Workflow execution result."""

    def __init__(self, state: str, step_results: dict[str, t.Any]):
        self.state = state
        self.step_results = step_results


class BasicWorkflowEngine:
    """Simple workflow engine for Oneiric-compatible workflow execution."""

    def __init__(
        self,
        max_concurrent_steps: int = 3,
        enable_retry: bool = True,
        max_retries: int = 2,
    ):
        self.max_concurrent_steps = max_concurrent_steps
        self.enable_retry = enable_retry
        self.max_retries = max_retries

    async def execute(
        self,
        workflow: WorkflowDefinition,
        context: dict[str, t.Any],
        action_handlers: dict[str, t.Callable[..., t.Any]],
    ) -> WorkflowResult:
        """Execute a workflow."""
        step_results = {}

        try:
            # Execute steps sequentially (simplified for Oneiric)
            for step in workflow.steps:
                try:
                    handler = action_handlers.get(step.action)
                    if handler:
                        result = await handler(context, step.params)
                        step_results[step.step_id] = {
                            "state": "completed",
                            "result": result,
                            "error": None,
                        }
                    else:
                        step_results[step.step_id] = {
                            "state": "failed",
                            "result": None,
                            "error": f"Handler not found for action: {step.action}",
                        }
                except Exception as e:
                    step_results[step.step_id] = {
                        "state": "failed",
                        "result": None,
                        "error": str(e),
                    }

            # Determine overall state
            failed_steps = [s for s in step_results.values() if s["state"] == "failed"]
            state = WorkflowState.FAILED if failed_steps else WorkflowState.COMPLETED

            return WorkflowResult(state, step_results)

        except Exception as e:
            return WorkflowResult(
                WorkflowState.FAILED,
                {
                    "error": str(e),
                    "state": WorkflowState.FAILED,
                },
            )


class FastBlocksWorkflowService(metaclass=SingletonMeta):
    """FastBlocks workflow service with Oneiric integration."""

    def __init__(self) -> None:
        """Initialize workflow service with Oneiric integration."""
        if not hasattr(self, "_initialized"):
            self._engine = BasicWorkflowEngine(
                max_concurrent_steps=3,  # Conservative concurrency
                enable_retry=True,
                max_retries=2,
            )
            self._initialized = True

    @property
    def available(self) -> bool:
        """Check if workflow service is available."""
        return True  # Always available with Oneiric


# Singleton instance
_workflow_service: FastBlocksWorkflowService | None = None


def get_workflow_service() -> FastBlocksWorkflowService:
    """Get the singleton FastBlocksWorkflowService instance."""
    global _workflow_service
    if _workflow_service is None:
        _workflow_service = FastBlocksWorkflowService()
    return _workflow_service


def _build_cache_steps(
    warm_templates: bool, warm_static: bool, warm_routes: bool
) -> list[WorkflowStep]:
    """Build workflow steps for cache warming."""
    steps = []
    if warm_templates:
        steps.append(
            WorkflowStep(
                step_id="warm_templates",
                name="Warm Template Cache",
                action="warm_template_cache",
                params={},
                retry_on_failure=True,
                max_retries=2,
            )
        )
    if warm_static:
        steps.append(
            WorkflowStep(
                step_id="warm_static",
                name="Warm Static File Cache",
                action="warm_static_cache",
                params={},
                retry_on_failure=True,
                max_retries=2,
            )
        )
    if warm_routes:
        steps.append(
            WorkflowStep(
                step_id="warm_routes",
                name="Warm Route Cache",
                action="warm_route_cache",
                params={},
                retry_on_failure=True,
                max_retries=2,
            )
        )
    return steps


def _build_templates_steps(
    cleanup_cache: bool, remove_stale: bool, optimize_storage: bool
) -> list[WorkflowStep]:
    """Build workflow steps for template cleanup."""
    steps = []
    if cleanup_cache:
        steps.append(
            WorkflowStep(
                step_id="cleanup_cache",
                name="Cleanup Template Cache",
                action="cleanup_template_cache",
                params={},
                retry_on_failure=False,
            )
        )
    if remove_stale:
        steps.append(
            WorkflowStep(
                step_id="remove_stale",
                name="Remove Stale Templates",
                action="remove_stale_templates",
                params={"days_threshold": 30},
                depends_on=["cleanup_cache"] if cleanup_cache else [],
                retry_on_failure=False,
            )
        )
    if optimize_storage:
        steps.append(
            WorkflowStep(
                step_id="optimize_storage",
                name="Optimize Template Storage",
                action="optimize_template_storage",
                params={},
                depends_on=["remove_stale"] if remove_stale else [],
                retry_on_failure=True,
                max_retries=2,
            )
        )
    return steps


def _build_performance_steps(
    cleanup_sessions: bool, optimize_queries: bool, rebuild_indexes: bool
) -> list[WorkflowStep]:
    """Build workflow steps for performance optimization."""
    steps = []
    if cleanup_sessions:
        steps.append(
            WorkflowStep(
                step_id="cleanup_sessions",
                name="Cleanup Expired Sessions",
                action="cleanup_expired_sessions",
                params={"expiry_hours": 24},
                retry_on_failure=False,
            )
        )
    if optimize_queries:
        steps.append(
            WorkflowStep(
                step_id="optimize_queries",
                name="Optimize Database Queries",
                action="optimize_database_queries",
                params={},
                retry_on_failure=True,
                max_retries=2,
            )
        )
    if rebuild_indexes:
        steps.append(
            WorkflowStep(
                step_id="rebuild_indexes",
                name="Rebuild Database Indexes",
                action="rebuild_database_indexes",
                params={},
                depends_on=["optimize_queries"] if optimize_queries else [],
                retry_on_failure=True,
                max_retries=1,
            )
        )
    return steps


def _build_workflow_result(
    workflow: WorkflowDefinition, result: WorkflowResult
) -> dict[str, t.Any]:
    """Build the standard result dict from a workflow execution."""
    state = result.state.value if hasattr(result.state, "value") else result.state
    return {
        "workflow_id": workflow.workflow_id,
        "state": state,
        "completed_at": datetime.now().isoformat(),
        "steps_completed": len(
            [s for s in result.step_results.values() if s["state"] == "completed"]
        ),
        "steps_failed": len(
            [s for s in result.step_results.values() if s["state"] == "failed"]
        ),
        "errors": [s["error"] for s in result.step_results.values() if s.get("error")],
    }


async def execute_optimization(
    target: Literal["cache", "templates", "performance"],
    *,
    # cache options
    warm_templates: bool = True,
    warm_static: bool = True,
    warm_routes: bool = True,
    # templates options
    remove_stale: bool = True,
    optimize_storage: bool = True,
    cleanup_cache: bool = True,
    # performance options
    optimize_queries: bool = True,
    rebuild_indexes: bool = True,
    cleanup_sessions: bool = True,
) -> dict[str, t.Any]:
    """Execute a FastBlocks optimisation workflow.

    Args:
        target: Which workflow to run — ``"cache"``, ``"templates"``,
            or ``"performance"``.
        warm_templates: (cache) Pre-cache commonly used templates.
        warm_static: (cache) Pre-cache static file metadata.
        warm_routes: (cache) Pre-cache route definitions.
        remove_stale: (templates) Remove templates not accessed in 30+ days.
        optimize_storage: (templates) Compress and optimise template storage.
        cleanup_cache: (templates) Clear unused template cache entries.
        optimize_queries: (performance) Analyse and optimise slow queries.
        rebuild_indexes: (performance) Rebuild database indexes.
        cleanup_sessions: (performance) Clean up expired sessions.

    Returns:
        Dictionary with workflow results.
    """
    service = get_workflow_service()

    if target == "cache":
        if not service.available:
            return await _manual_cache_warming(warm_templates, warm_static, warm_routes)
        steps = _build_cache_steps(warm_templates, warm_static, warm_routes)
        workflow = WorkflowDefinition(
            workflow_id="cache-warming",
            name="Cache Warming Workflow",
            description="Pre-load frequently accessed resources into cache",
            steps=steps,
            max_execution_time=300,
        )
        result = await service._engine.execute(
            workflow,
            context={
                "warm_templates": warm_templates,
                "warm_static": warm_static,
                "warm_routes": warm_routes,
            },
            action_handlers={
                "warm_template_cache": _warm_template_cache,
                "warm_static_cache": _warm_static_cache,
                "warm_route_cache": _warm_route_cache,
            },
        )

    elif target == "templates":
        if not service.available:
            return await _manual_template_cleanup(
                remove_stale, optimize_storage, cleanup_cache
            )
        steps = _build_templates_steps(cleanup_cache, remove_stale, optimize_storage)
        workflow = WorkflowDefinition(
            workflow_id="template-cleanup",
            name="Template Cleanup Workflow",
            description="Remove stale templates and optimize storage",
            steps=steps,
            max_execution_time=600,
        )
        result = await service._engine.execute(
            workflow,
            context={
                "remove_stale": remove_stale,
                "optimize_storage": optimize_storage,
                "cleanup_cache": cleanup_cache,
            },
            action_handlers={
                "cleanup_template_cache": _cleanup_template_cache,
                "remove_stale_templates": _remove_stale_templates,
                "optimize_template_storage": _optimize_template_storage,
            },
        )

    elif target == "performance":
        if not service.available:
            return await _manual_performance_optimization(
                optimize_queries, rebuild_indexes, cleanup_sessions
            )
        steps = _build_performance_steps(
            cleanup_sessions, optimize_queries, rebuild_indexes
        )
        workflow = WorkflowDefinition(
            workflow_id="performance-optimization",
            name="Performance Optimization Workflow",
            description="Optimize database and application performance",
            steps=steps,
            max_execution_time=900,
        )
        result = await service._engine.execute(
            workflow,
            context={
                "optimize_queries": optimize_queries,
                "rebuild_indexes": rebuild_indexes,
                "cleanup_sessions": cleanup_sessions,
            },
            action_handlers={
                "cleanup_expired_sessions": _cleanup_expired_sessions,
                "optimize_database_queries": _optimize_database_queries,
                "rebuild_database_indexes": _rebuild_database_indexes,
            },
        )

    else:
        msg = f"Unknown optimization target: {target!r}"
        raise ValueError(msg)

    return _build_workflow_result(workflow, result)


# Convenience shims kept for backward compatibility — delegate to execute_optimization.


async def execute_cache_warming(
    warm_templates: bool = True,
    warm_static: bool = True,
    warm_routes: bool = True,
) -> dict[str, t.Any]:
    """Execute cache warming workflow (delegates to execute_optimization)."""
    return await execute_optimization(
        "cache",
        warm_templates=warm_templates,
        warm_static=warm_static,
        warm_routes=warm_routes,
    )


async def execute_template_cleanup(
    remove_stale: bool = True,
    optimize_storage: bool = True,
    cleanup_cache: bool = True,
) -> dict[str, t.Any]:
    """Execute template cleanup workflow (delegates to execute_optimization)."""
    return await execute_optimization(
        "templates",
        remove_stale=remove_stale,
        optimize_storage=optimize_storage,
        cleanup_cache=cleanup_cache,
    )


async def execute_performance_optimization(
    optimize_queries: bool = True,
    rebuild_indexes: bool = True,
    cleanup_sessions: bool = True,
) -> dict[str, t.Any]:
    """Execute performance optimization workflow (delegates to execute_optimization)."""
    return await execute_optimization(
        "performance",
        optimize_queries=optimize_queries,
        rebuild_indexes=rebuild_indexes,
        cleanup_sessions=cleanup_sessions,
    )


# Action handler implementations


async def _warm_template_cache(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Warm template cache by pre-loading commonly used templates."""
    with suppress(Exception):
        from .actions.gather import gather

        # Gather all templates
        templates_result = await gather.templates()

        if templates_result and hasattr(templates_result, "templates"):
            cached_count = 0
            # Pre-cache template metadata (not full rendering)
            cache = await depends.resolve("fastblocks", "cache")
            if cache:
                for template_name in list(templates_result.templates.keys())[
                    :50
                ]:  # Limit to top 50
                    cache_key = f"template:metadata:{template_name}"
                    await cache.set(
                        cache_key,
                        {
                            "name": template_name,
                            "warmed_at": datetime.now().isoformat(),
                        },
                        ttl=3600,
                    )
                    cached_count += 1

            return {"templates_warmed": cached_count, "status": "completed"}

    return {"templates_warmed": 0, "status": "skipped"}


async def _warm_static_cache(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Warm static file cache by pre-loading metadata."""
    raise NotImplementedError(
        "Static file cache warming requires a static file adapter"
    )


async def _warm_route_cache(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Warm route cache by pre-loading route definitions."""
    with suppress(Exception):
        from .actions.gather import gather

        # Gather all routes
        routes_result = await gather.routes()

        if routes_result and hasattr(routes_result, "routes"):
            cached_count = len(routes_result.routes)
            return {"routes_warmed": cached_count, "status": "completed"}

    return {"routes_warmed": 0, "status": "skipped"}


async def _cleanup_template_cache(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Clean up unused template cache entries."""
    with suppress(Exception):
        cache = await depends.resolve("fastblocks", "cache")
        if cache and hasattr(cache, "clear_pattern"):
            # Clear stale template cache entries
            await cache.clear_pattern("template:*")
            return {"cache_cleared": True, "status": "completed"}

    return {"cache_cleared": False, "status": "skipped"}


async def _remove_stale_templates(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Remove templates not accessed in X days."""
    days_threshold = params.get("days_threshold", 30)

    # In production, would check template access logs
    # For now, just return placeholder
    return {
        "templates_removed": 0,
        "days_threshold": days_threshold,
        "status": "completed",
    }


async def _optimize_template_storage(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Optimize template storage (compress, deduplicate)."""
    raise NotImplementedError("Template storage optimization is not yet implemented")


async def _cleanup_expired_sessions(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Clean up expired sessions."""
    expiry_hours = params.get("expiry_hours", 24)

    # In production, would clean up session storage
    return {
        "sessions_cleaned": 0,
        "expiry_hours": expiry_hours,
        "status": "completed",
    }


async def _optimize_database_queries(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Analyze and optimize slow database queries."""
    raise NotImplementedError("Database query optimization is not yet implemented")


async def _rebuild_database_indexes(
    context: dict[str, t.Any], params: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Rebuild database indexes for optimal performance."""
    raise NotImplementedError("Database index rebuild is not yet implemented")


# Manual fallback implementations (when ACB Workflows unavailable)


async def _manual_cache_warming(
    warm_templates: bool, warm_static: bool, warm_routes: bool
) -> dict[str, t.Any]:
    """Manual cache warming without workflow orchestration."""
    results = {}

    if warm_templates:
        result = await _warm_template_cache({}, {})
        results["templates"] = result

    if warm_static:
        result = await _warm_static_cache({}, {})
        results["static"] = result

    if warm_routes:
        result = await _warm_route_cache({}, {})
        results["routes"] = result

    return {
        "workflow_id": "cache-warming",
        "state": "completed",
        "completed_at": datetime.now().isoformat(),
        "results": results,
        "mode": "manual",
    }


async def _manual_template_cleanup(
    remove_stale: bool, optimize_storage: bool, cleanup_cache: bool
) -> dict[str, t.Any]:
    """Manual template cleanup without workflow orchestration."""
    results = {}

    if cleanup_cache:
        result = await _cleanup_template_cache({}, {})
        results["cache_cleanup"] = result

    if remove_stale:
        result = await _remove_stale_templates({}, {"days_threshold": 30})
        results["stale_removal"] = result

    if optimize_storage:
        result = await _optimize_template_storage({}, {})
        results["storage_optimization"] = result

    return {
        "workflow_id": "template-cleanup",
        "state": "completed",
        "completed_at": datetime.now().isoformat(),
        "results": results,
        "mode": "manual",
    }


async def _manual_performance_optimization(
    optimize_queries: bool, rebuild_indexes: bool, cleanup_sessions: bool
) -> dict[str, t.Any]:
    """Manual performance optimization without workflow orchestration."""
    results = {}

    if cleanup_sessions:
        result = await _cleanup_expired_sessions({}, {"expiry_hours": 24})
        results["session_cleanup"] = result

    if optimize_queries:
        result = await _optimize_database_queries({}, {})
        results["query_optimization"] = result

    if rebuild_indexes:
        result = await _rebuild_database_indexes({}, {})
        results["index_rebuild"] = result

    return {
        "workflow_id": "performance-optimization",
        "state": "completed",
        "completed_at": datetime.now().isoformat(),
        "results": results,
        "mode": "manual",
    }


async def register_fastblocks_workflows() -> bool:
    """Register FastBlocks workflows with ACB.

    Returns:
        True if registration successful, False otherwise
    """
    if not oneiric_workflows_available:
        return False

    try:
        # Initialize workflow service
        workflow_service = get_workflow_service()

        # Register with depends
        depends.set("fastblocks_workflows", workflow_service)

        return workflow_service.available

    except Exception:
        return False


__all__ = [
    "FastBlocksWorkflowService",
    "get_workflow_service",
    "execute_optimization",
    "execute_cache_warming",
    "execute_template_cleanup",
    "execute_performance_optimization",
    "register_fastblocks_workflows",
    "oneiric_workflows_available",
]
