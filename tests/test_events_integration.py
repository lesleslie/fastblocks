"""Tests for FastBlocks ACB Events integration.

Tests the event-driven architecture integration including:
- Cache invalidation events
- Template render tracking
- HTMX update broadcasting
- Admin action auditing
"""

import pytest
from fastblocks._events_integration import (
    ACB_EVENTS_AVAILABLE,
    AdminActionHandler,
    AdminActionPayload,
    CacheInvalidationHandler,
    CacheInvalidationPayload,
    FastBlocksEventPublisher,
    FastBlocksEventType,
    HtmxUpdateHandler,
    HtmxUpdatePayload,
    TemplateRenderHandler,
    TemplateRenderPayload,
    get_event_publisher,
    register_fastblocks_event_handlers,
)


@pytest.fixture
def mock_cache_adapter():
    """Mock cache adapter."""

    class MockCache:
        def __init__(self):
            self.deleted_keys = []

        async def delete(self, key: str):
            self.deleted_keys.append(key)
            return True

    return MockCache()


@pytest.fixture
def sample_cache_event():
    """Sample cache invalidation event."""
    if not ACB_EVENTS_AVAILABLE:
        return None

    from acb.events import create_event

    return create_event(
        event_type=FastBlocksEventType.CACHE_INVALIDATED,
        source="test",
        payload={
            "cache_key": "template:home.html",
            "reason": "content_updated",
            "invalidated_by": "admin_user",
            "affected_templates": ["home.html", "layout.html"],
        },
    )


@pytest.fixture
def sample_template_event():
    """Sample template render event."""
    if not ACB_EVENTS_AVAILABLE:
        return None

    from acb.events import create_event

    return create_event(
        event_type=FastBlocksEventType.TEMPLATE_RENDERED,
        source="test",
        payload={
            "template_name": "dashboard.html",
            "render_time_ms": 45.2,
            "cache_hit": False,
            "context_size": 1024,
            "fragment_count": 3,
            "error": None,
        },
    )


@pytest.fixture
def sample_htmx_event():
    """Sample HTMX update event."""
    if not ACB_EVENTS_AVAILABLE:
        return None

    from acb.events import create_event

    return create_event(
        event_type=FastBlocksEventType.HTMX_REFRESH,
        source="test",
        payload={
            "update_type": "trigger",
            "target": "#user-list",
            "swap_method": "innerHTML",
            "trigger_name": "userUpdated",
            "trigger_data": {"user_id": 123},
        },
    )


@pytest.fixture
def sample_admin_event():
    """Sample admin action event."""
    if not ACB_EVENTS_AVAILABLE:
        return None

    from acb.events import create_event

    return create_event(
        event_type=FastBlocksEventType.ADMIN_ACTION,
        source="test",
        payload={
            "action_type": "delete",
            "user_id": "admin123",
            "resource_type": "post",
            "resource_id": "456",
            "changes": {"status": "deleted"},
            "ip_address": "192.168.1.1",
        },
    )


# Basic availability tests


@pytest.mark.integration
def test_acb_events_import():
    """Test that ACB events availability is detected."""
    # Should be True or False depending on ACB installation
    assert isinstance(ACB_EVENTS_AVAILABLE, bool)


@pytest.mark.integration
def test_event_types_defined():
    """Test that FastBlocks event types are defined."""
    assert hasattr(FastBlocksEventType, "CACHE_INVALIDATED")
    assert hasattr(FastBlocksEventType, "TEMPLATE_RENDERED")
    assert hasattr(FastBlocksEventType, "HTMX_REFRESH")
    assert hasattr(FastBlocksEventType, "ADMIN_ACTION")


# Payload dataclass tests


@pytest.mark.integration
def test_cache_invalidation_payload():
    """Test CacheInvalidationPayload creation."""
    payload = CacheInvalidationPayload(
        cache_key="test:key",
        reason="manual",
        invalidated_by="user123",
        affected_templates=["test.html"],
    )

    assert payload.cache_key == "test:key"
    assert payload.reason == "manual"
    assert payload.invalidated_by == "user123"
    assert payload.affected_templates == ["test.html"]


@pytest.mark.integration
def test_template_render_payload():
    """Test TemplateRenderPayload creation."""
    payload = TemplateRenderPayload(
        template_name="test.html",
        render_time_ms=25.5,
        cache_hit=True,
        context_size=512,
        fragment_count=2,
        error=None,
    )

    assert payload.template_name == "test.html"
    assert payload.render_time_ms == 25.5
    assert payload.cache_hit is True
    assert payload.context_size == 512


@pytest.mark.integration
def test_htmx_update_payload():
    """Test HtmxUpdatePayload creation."""
    payload = HtmxUpdatePayload(
        update_type="refresh",
        target="#content",
        swap_method="innerHTML",
        trigger_name="refreshed",
        trigger_data={"count": 5},
    )

    assert payload.update_type == "refresh"
    assert payload.target == "#content"
    assert payload.trigger_data == {"count": 5}


@pytest.mark.integration
def test_admin_action_payload():
    """Test AdminActionPayload creation."""
    payload = AdminActionPayload(
        action_type="update",
        user_id="admin456",
        resource_type="article",
        resource_id="789",
        changes={"title": "New Title"},
        ip_address="10.0.0.1",
    )

    assert payload.action_type == "update"
    assert payload.user_id == "admin456"
    assert payload.resource_type == "article"


# Handler tests


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_cache_invalidation_handler(mock_cache_adapter, sample_cache_event):
    """Test cache invalidation handler."""
    from unittest.mock import patch

    from acb.events import EventHandlerResult

    with patch("fastblocks._events_integration.depends.get") as mock_depends:
        mock_depends.return_value = mock_cache_adapter

        handler = CacheInvalidationHandler()
        result = await handler.handle(sample_cache_event)

        assert isinstance(result, EventHandlerResult)
        assert result.success is True
        assert "template:home.html" in mock_cache_adapter.deleted_keys
        assert "template:home.html" in mock_cache_adapter.deleted_keys
        assert "template:layout.html" in mock_cache_adapter.deleted_keys


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_template_render_handler(sample_template_event):
    """Test template render handler."""
    from acb.events import EventHandlerResult

    handler = TemplateRenderHandler()
    result = await handler.handle(sample_template_event)

    assert isinstance(result, EventHandlerResult)
    assert result.success is True
    assert "dashboard.html" in handler.metrics

    # Get stats
    stats = handler.get_template_stats("dashboard.html")
    assert stats["total_renders"] == 1
    assert stats["avg_render_time_ms"] == 45.2
    assert stats["cache_hit_ratio"] == 0.0


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_template_render_handler_stats():
    """Test template render handler statistics collection."""
    from acb.events import create_event

    handler = TemplateRenderHandler()

    # Add multiple renders
    for i in range(5):
        event = create_event(
            event_type=FastBlocksEventType.TEMPLATE_RENDERED,
            source="test",
            payload={
                "template_name": "test.html",
                "render_time_ms": 10.0 + i,
                "cache_hit": i % 2 == 0,  # Alternate cache hits
                "context_size": 100,
                "fragment_count": 1,
                "error": None,
            },
        )
        await handler.handle(event)

    stats = handler.get_template_stats("test.html")
    assert stats["total_renders"] == 5
    assert stats["min_render_time_ms"] == 10.0
    assert stats["max_render_time_ms"] == 14.0
    assert stats["cache_hit_ratio"] == 0.6  # 3 out of 5


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_htmx_update_handler(sample_htmx_event):
    """Test HTMX update handler."""
    from acb.events import EventHandlerResult

    handler = HtmxUpdateHandler()
    result = await handler.handle(sample_htmx_event)

    assert isinstance(result, EventHandlerResult)
    assert result.success is True
    assert "headers" in result.data
    assert result.data["headers"]["HX-Trigger"] == "userUpdated"


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_htmx_refresh_event():
    """Test HTMX refresh event handling."""
    from acb.events import create_event

    handler = HtmxUpdateHandler()

    event = create_event(
        event_type=FastBlocksEventType.HTMX_REFRESH,
        source="test",
        payload={
            "update_type": "refresh",
            "target": "#main-content",
            "swap_method": None,
            "trigger_name": None,
            "trigger_data": None,
        },
    )

    result = await handler.handle(event)
    assert result.success is True
    assert result.data["headers"]["HX-Trigger"] == "refresh"
    assert result.data["headers"]["HX-Refresh"] == "true"


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_htmx_redirect_event():
    """Test HTMX redirect event handling."""
    from acb.events import create_event

    handler = HtmxUpdateHandler()

    event = create_event(
        event_type=FastBlocksEventType.HTMX_REFRESH,
        source="test",
        payload={
            "update_type": "redirect",
            "target": "/dashboard",
            "swap_method": None,
            "trigger_name": None,
            "trigger_data": None,
        },
    )

    result = await handler.handle(event)
    assert result.success is True
    assert result.data["headers"]["HX-Redirect"] == "/dashboard"


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_admin_action_handler(sample_admin_event):
    """Test admin action handler."""
    from acb.events import EventHandlerResult

    handler = AdminActionHandler()
    result = await handler.handle(sample_admin_event)

    assert isinstance(result, EventHandlerResult)
    assert result.success is True
    assert len(handler.audit_log) == 1

    # Get recent actions
    recent = handler.get_recent_actions(limit=10)
    assert len(recent) == 1
    assert recent[0]["action_type"] == "delete"
    assert recent[0]["user_id"] == "admin123"


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_admin_action_handler_limit():
    """Test admin action handler audit log limit."""
    from acb.events import create_event

    handler = AdminActionHandler()

    # Add 1100 actions (exceeds 1000 limit)
    for i in range(1100):
        event = create_event(
            event_type=FastBlocksEventType.ADMIN_ACTION,
            source="test",
            payload={
                "action_type": "test",
                "user_id": f"user{i}",
                "resource_type": "test",
                "resource_id": str(i),
                "changes": None,
                "ip_address": None,
            },
        )
        await handler.handle(event)

    # Should only keep last 1000
    assert len(handler.audit_log) == 1000
    recent = handler.get_recent_actions(limit=1)
    assert recent[0]["user_id"] == "user1099"  # Most recent


# Publisher tests


@pytest.mark.integration
def test_event_publisher_singleton():
    """Test that FastBlocksEventPublisher is a singleton."""
    publisher1 = get_event_publisher()
    publisher2 = get_event_publisher()

    if ACB_EVENTS_AVAILABLE:
        assert publisher1 is publisher2
    else:
        assert publisher1 is None
        assert publisher2 is None


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_publisher_cache_invalidation():
    """Test publishing cache invalidation event."""
    publisher = FastBlocksEventPublisher()

    # Should not raise exception even if publisher not fully initialized
    result = await publisher.publish_cache_invalidation(
        cache_key="test:key",
        reason="test",
        invalidated_by="test_user",
        affected_templates=["test.html"],
    )

    # Result depends on whether publisher is initialized
    assert isinstance(result, bool)


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_publisher_template_render():
    """Test publishing template render event."""
    publisher = FastBlocksEventPublisher()

    result = await publisher.publish_template_render(
        template_name="test.html",
        render_time_ms=25.0,
        cache_hit=True,
        context_size=512,
        fragment_count=2,
        error=None,
    )

    assert isinstance(result, bool)


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_publisher_htmx_update():
    """Test publishing HTMX update event."""
    publisher = FastBlocksEventPublisher()

    result = await publisher.publish_htmx_update(
        update_type="refresh",
        target="#content",
        swap_method="innerHTML",
        trigger_name="refreshed",
        trigger_data={"count": 5},
    )

    assert isinstance(result, bool)


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_publisher_admin_action():
    """Test publishing admin action event."""
    publisher = FastBlocksEventPublisher()

    result = await publisher.publish_admin_action(
        action_type="update",
        user_id="admin123",
        resource_type="post",
        resource_id="456",
        changes={"title": "Updated"},
        ip_address="192.168.1.1",
    )

    assert isinstance(result, bool)


# Registration tests


@pytest.mark.asyncio
@pytest.mark.integration
async def test_register_event_handlers_without_acb():
    """Test event handler registration when ACB not available."""
    if not ACB_EVENTS_AVAILABLE:
        result = await register_fastblocks_event_handlers()
        assert result is False


@pytest.mark.asyncio
@pytest.mark.skipif(not ACB_EVENTS_AVAILABLE, reason="ACB Events not available")
@pytest.mark.integration
async def test_register_event_handlers_with_acb():
    """Test event handler registration when ACB available."""
    # Should return True or False depending on publisher initialization
    result = await register_fastblocks_event_handlers()
    assert isinstance(result, bool)


# Graceful degradation tests


@pytest.mark.integration
def test_handlers_without_acb():
    """Test that handlers handle missing ACB gracefully."""
    if not ACB_EVENTS_AVAILABLE:
        # Should not raise exceptions
        handler1 = CacheInvalidationHandler()
        handler2 = TemplateRenderHandler()
        handler3 = HtmxUpdateHandler()
        handler4 = AdminActionHandler()

        assert handler1 is not None
        assert handler2 is not None
        assert handler3 is not None
        assert handler4 is not None


@pytest.mark.asyncio
@pytest.mark.integration
async def test_handler_handle_without_acb():
    """Test handler.handle() returns None when ACB unavailable."""
    if not ACB_EVENTS_AVAILABLE:
        handler = TemplateRenderHandler()
        result = await handler.handle(None)
        assert result is None


@pytest.mark.integration
def test_get_event_publisher_without_acb():
    """Test get_event_publisher() returns None when ACB unavailable."""
    if not ACB_EVENTS_AVAILABLE:
        publisher = get_event_publisher()
        assert publisher is None
