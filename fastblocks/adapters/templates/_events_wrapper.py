"""Event tracking wrapper for template rendering operations.

This module provides decorators and wrappers to integrate ACB Events
with template rendering, tracking performance metrics automatically.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-10-01
"""

import functools
import sys
import time
import typing as t
from contextlib import suppress

from acb.depends import depends


def track_template_render(
    func: t.Callable[..., t.Awaitable[t.Any]],
) -> t.Callable[..., t.Awaitable[t.Any]]:
    """Decorator to track template rendering performance.

    Publishes template render events with performance metrics.
    Gracefully degrades if events integration unavailable.

    Usage:
        @track_template_render
        async def render_template(self, template_name, context):
            ...
    """

    @functools.wraps(func)
    async def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
        # Extract arguments
        template_name = _extract_template_name(args, kwargs)
        context = _extract_context(args, kwargs)

        # Track render time
        start_time = time.perf_counter()

        try:
            # Call the original function
            result = await func(*args, **kwargs)

            # Calculate and publish success metrics
            render_time_ms = (time.perf_counter() - start_time) * 1000
            await _publish_render_event(
                template_name=template_name,
                render_time_ms=render_time_ms,
                context=context,
                error=None,
            )

            return result

        except Exception as e:
            # Calculate and publish error metrics
            render_time_ms = (time.perf_counter() - start_time) * 1000
            await _publish_render_event(
                template_name=template_name,
                render_time_ms=render_time_ms,
                context=context,
                error=str(e),
            )
            raise

    return wrapper


def _extract_template_name(
    args: tuple[t.Any, ...], kwargs: dict[str, t.Any]
) -> str | None:
    """Extract template name from function arguments."""
    # Check kwargs first (more explicit)
    for key in ("template", "name"):
        if key in kwargs:
            template_name: str | None = kwargs[key]
            return template_name

    # Check positional args
    if len(args) > 2 and isinstance(args[2], str):
        return args[2]

    return None


def _extract_context(
    args: tuple[t.Any, ...], kwargs: dict[str, t.Any]
) -> dict[str, t.Any] | None:
    """Extract context dictionary from function arguments."""
    # Check kwargs first
    if "context" in kwargs and isinstance(kwargs["context"], dict):
        return kwargs["context"]

    # Check positional args
    if len(args) > 3 and isinstance(args[3], dict):
        return args[3]

    return None


async def _publish_render_event(
    template_name: str | None,
    render_time_ms: float,
    context: dict[str, t.Any] | None,
    error: str | None,
) -> None:
    """Publish template render event with metrics."""
    if not template_name:
        return

    context_size = sys.getsizeof(context) if context else 0
    cache_hit = render_time_ms < 5.0 if not error else False

    with suppress(Exception):
        from ..._events_integration import get_event_publisher

        publisher = get_event_publisher()
        if publisher:
            await publisher.publish_template_render(
                template_name=template_name,
                render_time_ms=render_time_ms,
                cache_hit=cache_hit,
                context_size=context_size,
                fragment_count=0,  # TODO: Extract from result
                error=error,
            )


async def publish_cache_invalidation(
    cache_key: str,
    reason: str = "manual",
    invalidated_by: str | None = None,
    affected_templates: list[str] | None = None,
) -> bool:
    """Publish cache invalidation event.

    Helper function for cache operations to broadcast invalidation events.

    Args:
        cache_key: The cache key being invalidated
        reason: Reason for invalidation (e.g., "content_updated", "manual")
        invalidated_by: User/system that triggered invalidation
        affected_templates: List of template names affected by this invalidation

    Returns:
        True if event published successfully, False otherwise
    """
    with suppress(Exception):
        from ..._events_integration import get_event_publisher

        publisher = get_event_publisher()
        if publisher:
            return await publisher.publish_cache_invalidation(
                cache_key=cache_key,
                reason=reason,
                invalidated_by=invalidated_by,
                affected_templates=affected_templates,
            )

    return False


async def publish_htmx_refresh(
    target: str,
    swap_method: str | None = None,
) -> bool:
    """Publish HTMX refresh event to connected clients.

    Args:
        target: CSS selector for element to refresh
        swap_method: How to swap content ("innerHTML", "outerHTML", etc.)

    Returns:
        True if event published successfully, False otherwise
    """
    with suppress(Exception):
        from ..._events_integration import get_event_publisher

        publisher = get_event_publisher()
        if publisher:
            return await publisher.publish_htmx_update(
                update_type="refresh",
                target=target,
                swap_method=swap_method,
            )

    return False


async def publish_htmx_trigger(
    trigger_name: str,
    trigger_data: dict[str, t.Any] | None = None,
    target: str | None = None,
) -> bool:
    """Publish custom HTMX trigger event.

    Args:
        trigger_name: Name of the custom event
        trigger_data: Data to send with the event
        target: Optional CSS selector for targeted delivery

    Returns:
        True if event published successfully, False otherwise
    """
    with suppress(Exception):
        from ..._events_integration import get_event_publisher

        publisher = get_event_publisher()
        if publisher:
            return await publisher.publish_htmx_update(
                update_type="trigger",
                trigger_name=trigger_name,
                trigger_data=trigger_data,
                target=target,
            )

    return False


async def publish_admin_action(
    action_type: str,
    user_id: str,
    resource_type: str | None = None,
    resource_id: str | None = None,
    changes: dict[str, t.Any] | None = None,
    ip_address: str | None = None,
) -> bool:
    """Publish admin action event for audit logging.

    Args:
        action_type: Type of action ("create", "update", "delete", "login", "logout")
        user_id: ID of user performing the action
        resource_type: Type of resource being modified
        resource_id: ID of specific resource
        changes: Dictionary of changes made
        ip_address: IP address of the user

    Returns:
        True if event published successfully, False otherwise
    """
    with suppress(Exception):
        from ..._events_integration import get_event_publisher

        publisher = get_event_publisher()
        if publisher:
            return await publisher.publish_admin_action(
                action_type=action_type,
                user_id=user_id,
                resource_type=resource_type,
                resource_id=resource_id,
                changes=changes,
                ip_address=ip_address,
            )

    return False


def get_template_metrics(template_name: str) -> dict[str, t.Any]:
    """Get performance metrics for a specific template.

    Args:
        template_name: Name of the template to get stats for

    Returns:
        Dictionary with performance statistics or empty dict if unavailable
    """
    with suppress(Exception):
        # Get the template metrics handler
        handler = depends.get_sync("template_metrics")
        if handler and hasattr(handler, "get_template_stats"):
            stats: dict[str, t.Any] = handler.get_template_stats(template_name)
            return stats

    return {}


def get_recent_admin_actions(limit: int = 50) -> list[dict[str, t.Any]]:
    """Get recent admin actions from audit log.

    Args:
        limit: Maximum number of actions to return

    Returns:
        List of recent admin actions or empty list if unavailable
    """
    with suppress(Exception):
        # Get the admin audit handler
        handler = depends.get_sync("admin_audit")
        if handler and hasattr(handler, "get_recent_actions"):
            actions: list[dict[str, t.Any]] = handler.get_recent_actions(limit=limit)
            return actions

    return []
