"""Oneiric Events system integration for FastBlocks.

This module provides FastBlocks components with an event-driven architecture,
enabling reactive updates, cache invalidation, and admin action tracking.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-10-01
"""

import operator
import typing as t
from contextlib import suppress
from dataclasses import dataclass
from uuid import UUID

# Oneiric imports for dependency injection
from oneiric.core.resolution import Resolver
from fastblocks.adapters.oneiric_helper import register_candidate

# Custom Oneiric-compatible events system
depends = Resolver()

# Event system availability
oneiric_events_available = True


# Custom Oneiric-compatible Event System
class EventPriority:
    """Event priority levels."""

    LOW = 1
    NORMAL = 2
    HIGH = 3
    CRITICAL = 4


class EventHandlerResult:
    """Result of event handling."""

    def __init__(
        self,
        success: bool,
        message: str,
        error: str | None = None,
        data: dict[str, t.Any] | None = None,
    ):
        self.success = success
        self.message = message
        self.error = error
        self.data = data or {}


class EventSubscription:
    """Event subscription."""

    def __init__(self, event_type: str, handler: t.Any):
        self.event_type = event_type
        self.handler = handler


class Event:
    """Event object."""

    def __init__(
        self,
        event_type: str,
        source: str,
        payload: dict[str, t.Any],
        priority: EventPriority,
    ):
        self.event_type = event_type
        self.source = source
        self.payload = payload
        self.priority = priority


class EventPublisher:
    """Event publisher for Oneiric-compatible event system."""

    def __init__(self) -> None:
        self.subscriptions: dict[str, list[EventSubscription]] = {}

    async def publish(self, event: Event) -> bool:
        """Publish an event to all subscribers."""
        try:
            handlers = self.subscriptions.get(event.event_type, [])

            for subscription in handlers:
                await subscription.handler.handle(event)

            return True
        except Exception:
            return False

    async def subscribe(self, subscription: EventSubscription) -> bool:
        """Subscribe to an event type."""
        try:
            if subscription.event_type not in self.subscriptions:
                self.subscriptions[subscription.event_type] = []

            self.subscriptions[subscription.event_type].append(subscription)
            return True
        except Exception:
            return False


def create_event(
    event_type: str, source: str, payload: dict[str, t.Any], priority: EventPriority
) -> Event:
    """Create an event."""
    return Event(event_type, source, payload, priority)


# FastBlocks Event Types
class FastBlocksEventType:
    """Event types emitted by FastBlocks components."""

    # Cache events
    CACHE_INVALIDATED = "fastblocks.cache.invalidated"
    CACHE_CLEARED = "fastblocks.cache.cleared"

    # Template events
    TEMPLATE_RENDERED = "fastblocks.template.rendered"
    TEMPLATE_ERROR = "fastblocks.template.error"

    # HTMX events (server-sent updates)
    HTMX_REFRESH = "fastblocks.htmx.refresh"
    HTMX_REDIRECT = "fastblocks.htmx.redirect"
    HTMX_TRIGGER = "fastblocks.htmx.trigger"

    # Admin events
    ADMIN_ACTION = "fastblocks.admin.action"
    ADMIN_LOGIN = "fastblocks.admin.login"
    ADMIN_LOGOUT = "fastblocks.admin.logout"

    # Route events
    ROUTE_REGISTERED = "fastblocks.route.registered"
    ROUTE_ACCESSED = "fastblocks.route.accessed"


@dataclass
class CacheInvalidationPayload:
    """Payload for cache invalidation events."""

    cache_key: str
    reason: str
    invalidated_by: str | None = None
    affected_templates: list[str] | None = None


@dataclass
class TemplateRenderPayload:
    """Payload for template render events."""

    template_name: str
    render_time_ms: float
    cache_hit: bool
    context_size: int
    fragment_count: int
    error: str | None = None


@dataclass
class HtmxUpdatePayload:
    """Payload for HTMX update events."""

    update_type: str  # "refresh", "redirect", "trigger"
    target: str | None = None  # CSS selector or URL
    swap_method: str | None = None  # "innerHTML", "outerHTML", etc.
    trigger_name: str | None = None
    trigger_data: dict[str, t.Any] | None = None


@dataclass
class AdminActionPayload:
    """Payload for admin action events."""

    action_type: str  # "create", "update", "delete", "login", "logout"
    user_id: str
    resource_type: str | None = None
    resource_id: str | None = None
    changes: dict[str, t.Any] | None = None
    ip_address: str | None = None


class CacheInvalidationHandler:
    """Handler for cache invalidation events."""

    def __init__(self, cache: t.Any | None = None) -> None:
        self.cache = cache

    async def handle(self, event: Event) -> t.Any:
        """Handle cache invalidation event."""
        if not acb_events_available:
            return None

        try:
            payload = CacheInvalidationPayload(**event.payload)

            # Invalidate the cache key
            if self.cache:
                await self.cache.delete(payload.cache_key)

                # Also invalidate related template caches if specified
                if payload.affected_templates:
                    for template_name in payload.affected_templates:
                        template_key = f"template:{template_name}"
                        await self.cache.delete(template_key)

            return EventHandlerResult(
                success=True,
                message=f"Invalidated cache key: {payload.cache_key}",
            )

        except Exception as e:
            return EventHandlerResult(
                success=False,
                error=str(e),
                message=f"Failed to invalidate cache: {e}",
            )


class TemplateRenderHandler:
    """Handler for template render events - collects performance metrics."""

    def __init__(self) -> None:
        self.metrics: dict[str, list[TemplateRenderPayload]] = {}

    async def handle(self, event: Event) -> t.Any:
        """Handle template render event."""
        if not acb_events_available:
            return None

        try:
            payload = TemplateRenderPayload(**event.payload)

            # Store metrics for performance analysis
            if payload.template_name not in self.metrics:
                self.metrics[payload.template_name] = []

            self.metrics[payload.template_name].append(payload)

            # Keep only last 100 renders per template
            if len(self.metrics[payload.template_name]) > 100:
                self.metrics[payload.template_name] = self.metrics[
                    payload.template_name
                ][-100:]

            return EventHandlerResult(
                success=True,
                message=f"Recorded render metrics for {payload.template_name}",
            )

        except Exception as e:
            return EventHandlerResult(
                success=False,
                error=str(e),
                message=f"Failed to record metrics: {e}",
            )

    def get_template_stats(self, template_name: str) -> dict[str, t.Any]:
        """Get performance statistics for a template."""
        if template_name not in self.metrics:
            return {}

        renders = self.metrics[template_name]
        render_times = [r.render_time_ms for r in renders]
        cache_hits = sum(1 for r in renders if r.cache_hit)

        return {
            "total_renders": len(renders),
            "avg_render_time_ms": sum(render_times) / len(render_times),
            "min_render_time_ms": min(render_times),
            "max_render_time_ms": max(render_times),
            "cache_hit_ratio": cache_hits / len(renders),
            "recent_errors": [r.error for r in renders[-10:] if r.error],
        }


class HtmxUpdateHandler:
    """Handler for HTMX update events - broadcasts to connected clients."""

    def __init__(self) -> None:
        self.active_connections: set[t.Any] = set()  # WebSocket connections

    async def handle(self, event: Event) -> t.Any:
        """Handle HTMX update event."""
        if not acb_events_available:
            return None

        try:
            payload = HtmxUpdatePayload(**event.payload)

            # Build HTMX headers for server-sent event
            headers = {}

            if payload.update_type == "refresh" and payload.target:
                headers["HX-Trigger"] = "refresh"
                headers["HX-Refresh"] = "true"

            elif payload.update_type == "redirect" and payload.target:
                headers["HX-Redirect"] = payload.target

            elif payload.update_type == "trigger" and payload.trigger_name:
                headers["HX-Trigger"] = payload.trigger_name
                if payload.trigger_data:
                    import json

                    headers["HX-Trigger-Data"] = json.dumps(payload.trigger_data)

            # Broadcast to all connected clients
            # Note: Actual WebSocket broadcast would happen in route handlers
            # This handler just prepares the event data

            return EventHandlerResult(
                success=True,
                message=f"Prepared HTMX {payload.update_type} event",
                data={"headers": headers},
            )

        except Exception as e:
            return EventHandlerResult(
                success=False,
                error=str(e),
                message=f"Failed to prepare HTMX event: {e}",
            )


class AdminActionHandler:
    """Handler for admin action events - audit logging."""

    def __init__(self) -> None:
        self.audit_log: list[tuple[float, AdminActionPayload]] = []

    async def handle(self, event: Event) -> t.Any:
        """Handle admin action event."""
        if not acb_events_available:
            return None

        try:
            import time

            payload = AdminActionPayload(**event.payload)

            # Store in audit log
            self.audit_log.append((time.time(), payload))

            # Keep only last 1000 actions
            if len(self.audit_log) > 1000:
                self.audit_log = self.audit_log[-1000:]

            # In production, this would also:
            # - Write to database audit table
            # - Send to monitoring/alerting system
            # - Trigger security checks for sensitive actions

            return EventHandlerResult(
                success=True,
                message=f"Logged admin action: {payload.action_type}",
            )

        except Exception as e:
            return EventHandlerResult(
                success=False,
                error=str(e),
                message=f"Failed to log admin action: {e}",
            )

    def get_recent_actions(self, limit: int = 50) -> list[dict[str, t.Any]]:
        """Get recent admin actions."""
        import time

        now = time.time()
        recent = sorted(self.audit_log, key=operator.itemgetter(0), reverse=True)[
            :limit
        ]

        return [
            {
                "timestamp": timestamp,
                "age_seconds": now - timestamp,
                "action_type": payload.action_type,
                "user_id": payload.user_id,
                "resource_type": payload.resource_type,
                "resource_id": payload.resource_id,
            }
            for timestamp, payload in recent
        ]


class FastBlocksEventPublisher:
    """Simplified event publisher for FastBlocks components."""

    _instance: t.ClassVar["FastBlocksEventPublisher | None"] = None
    _publisher: EventPublisher | None = None

    def __new__(cls) -> "FastBlocksEventPublisher":
        """Singleton pattern for event publisher."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self, config: t.Any | None = None) -> None:
        self.config = config
        self.source = "fastblocks"

        # Initialize publisher lazily
        if self._publisher is None:
            with suppress(Exception):
                self._publisher = EventPublisher()

    async def publish_cache_invalidation(
        self,
        cache_key: str,
        reason: str,
        invalidated_by: str | None = None,
        affected_templates: list[str] | None = None,
    ) -> bool:
        """Publish cache invalidation event."""
        if not acb_events_available or self._publisher is None:
            return False

        try:
            event = create_event(
                event_type=FastBlocksEventType.CACHE_INVALIDATED,
                source=self.source,
                payload={
                    "cache_key": cache_key,
                    "reason": reason,
                    "invalidated_by": invalidated_by,
                    "affected_templates": affected_templates,
                },
                priority=EventPriority.HIGH,
            )

            await self._publisher.publish(event)
            return True

        except Exception:
            return False

    async def publish_template_render(
        self,
        template_name: str,
        render_time_ms: float,
        cache_hit: bool,
        context_size: int,
        fragment_count: int,
        error: str | None = None,
    ) -> bool:
        """Publish template render event."""
        if not acb_events_available or self._publisher is None:
            return False

        try:
            event_type = (
                FastBlocksEventType.TEMPLATE_ERROR
                if error
                else FastBlocksEventType.TEMPLATE_RENDERED
            )

            event = create_event(
                event_type=event_type,
                source=self.source,
                payload={
                    "template_name": template_name,
                    "render_time_ms": render_time_ms,
                    "cache_hit": cache_hit,
                    "context_size": context_size,
                    "fragment_count": fragment_count,
                    "error": error,
                },
                priority=EventPriority.NORMAL,
            )

            await self._publisher.publish(event)
            return True

        except Exception:
            return False

    async def publish_htmx_update(
        self,
        update_type: str,
        target: str | None = None,
        swap_method: str | None = None,
        trigger_name: str | None = None,
        trigger_data: dict[str, t.Any] | None = None,
    ) -> bool:
        """Publish HTMX update event."""
        if not acb_events_available or self._publisher is None:
            return False

        try:
            event = create_event(
                event_type=FastBlocksEventType.HTMX_REFRESH,
                source=self.source,
                payload={
                    "update_type": update_type,
                    "target": target,
                    "swap_method": swap_method,
                    "trigger_name": trigger_name,
                    "trigger_data": trigger_data,
                },
                priority=EventPriority.HIGH,
            )

            await self._publisher.publish(event)
            return True

        except Exception:
            return False

    async def publish_admin_action(
        self,
        action_type: str,
        user_id: str,
        resource_type: str | None = None,
        resource_id: str | None = None,
        changes: dict[str, t.Any] | None = None,
        ip_address: str | None = None,
    ) -> bool:
        """Publish admin action event."""
        if not acb_events_available or self._publisher is None:
            return False

        try:
            event = create_event(
                event_type=FastBlocksEventType.ADMIN_ACTION,
                source=self.source,
                payload={
                    "action_type": action_type,
                    "user_id": user_id,
                    "resource_type": resource_type,
                    "resource_id": resource_id,
                    "changes": changes,
                    "ip_address": ip_address,
                },
                priority=EventPriority.CRITICAL,
            )

            await self._publisher.publish(event)
            return True

        except Exception:
            return False


async def register_fastblocks_event_handlers() -> bool:
    """Register all FastBlocks event handlers with Oneiric event system.

    Returns:
        True if registration successful, False if event system unavailable
    """
    try:
        publisher = FastBlocksEventPublisher()

        if publisher._publisher is None:
            return False

        # Register event handlers
        cache_handler = CacheInvalidationHandler()
        template_handler = TemplateRenderHandler()
        htmx_handler = HtmxUpdateHandler()
        admin_handler = AdminActionHandler()

        # Subscribe handlers to their event types
        await publisher._publisher.subscribe(
            EventSubscription(
                event_type=FastBlocksEventType.CACHE_INVALIDATED,
                handler=cache_handler,
            )
        )

        await publisher._publisher.subscribe(
            EventSubscription(
                event_type=FastBlocksEventType.TEMPLATE_RENDERED,
                handler=template_handler,
            )
        )

        await publisher._publisher.subscribe(
            EventSubscription(
                event_type=FastBlocksEventType.TEMPLATE_ERROR,
                handler=template_handler,
            )
        )

        await publisher._publisher.subscribe(
            EventSubscription(
                event_type=FastBlocksEventType.HTMX_REFRESH,
                handler=htmx_handler,
            )
        )

        await publisher._publisher.subscribe(
            EventSubscription(
                event_type=FastBlocksEventType.ADMIN_ACTION,
                handler=admin_handler,
            )
        )

        # Store handlers in depends for retrieval
        register_candidate(
            depends,
            domain="fastblocks",
            key="template_handler",
            factory=lambda: template_handler,
            metadata={
                "class": "TemplateEventHandler",
                "module": "fastblocks._events_integration",
            },
        )
        register_candidate(
            depends,
            domain="fastblocks",
            key="admin_handler",
            factory=lambda: admin_handler,
            metadata={
                "class": "AdminEventHandler",
                "module": "fastblocks._events_integration",
            },
        )

        return True

    except Exception:
        # Graceful degradation if registration fails
        return False


def get_event_publisher() -> FastBlocksEventPublisher | None:
    """Get the FastBlocks event publisher instance.

    Returns:
        Event publisher instance
    """
    return FastBlocksEventPublisher()


# Module metadata for Oneiric compatibility
MODULE_ID = UUID("01937d88-0000-7000-8000-000000000002")
MODULE_STATUS = "STABLE"  # Oneiric-compatible status
