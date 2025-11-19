"""Tests for FastBlocks HTMX template filters."""

from unittest.mock import Mock, patch

import pytest
from fastblocks.adapters.templates._filters import (
    htmx_attrs,
    htmx_component,
    htmx_error_container,
    htmx_form,
    htmx_icon_toggle,
    htmx_img_swap,
    htmx_infinite_scroll,
    htmx_lazy_load,
    htmx_modal,
    htmx_retry_trigger,
    htmx_search,
    htmx_validation_feedback,
    htmx_ws_connect,
)


@pytest.mark.unit
class TestEnhancedHtmxAttrs:
    """Test enhanced htmx_attrs filter."""

    def test_basic_htmx_attrs(self):
        """Test basic HTMX attribute generation."""
        result = htmx_attrs(get="/api/data", target="#content")
        assert 'hx-get="/api/data"' in result
        assert 'hx-target="#content"' in result

    def test_enhanced_htmx_attrs(self):
        """Test enhanced HTMX attributes."""
        result = htmx_attrs(
            get="/api/data",
            select=".content",
            sync="closest form:abort",
            disabled_elt="button",
        )
        assert 'hx-get="/api/data"' in result
        assert 'hx-select=".content"' in result
        assert 'hx-sync="closest form:abort"' in result
        assert 'hx-disabled-elt="button"' in result

    def test_custom_attributes(self):
        """Test custom attribute mapping."""
        result = htmx_attrs(custom_attr="value")
        assert 'hx-custom-attr="value"' in result


@pytest.mark.unit
class TestHtmxComponent:
    """Test htmx_component filter."""

    @patch("fastblocks.adapters.templates.filters.depends")
    @patch("fastblocks.adapters.templates.filters.style_class")
    def test_htmx_component_basic(self, mock_style_class, mock_depends):
        """Test basic HTMX component generation."""
        mock_style_class.return_value = "card shadow-md"

        result = htmx_component(
            "card", get="/api/details/123", target="#details", variant="primary"
        )

        assert 'class="card shadow-md"' in result
        assert 'hx-get="/api/details/123"' in result
        assert 'hx-target="#details"' in result

    @patch("fastblocks.adapters.templates.filters.style_class")
    def test_htmx_component_no_style_adapter(self, mock_style_class):
        """Test HTMX component without style adapter."""
        mock_style_class.return_value = "button"

        result = htmx_component("button", post="/api/action")

        assert 'class="button"' in result
        assert 'hx-post="/api/action"' in result


@pytest.mark.unit
class TestHtmxForm:
    """Test htmx_form filter."""

    def test_htmx_form_basic(self):
        """Test basic HTMX form generation."""
        result = htmx_form("/users/create")

        assert 'hx-post="/users/create"' in result
        assert 'hx-swap="outerHTML"' in result
        assert 'hx-indicator="#form-loading"' in result

    def test_htmx_form_with_validation(self):
        """Test HTMX form with validation target."""
        result = htmx_form(
            "/users/create", validation_target="#form-errors", target="#form-container"
        )

        assert 'hx-post="/users/create"' in result
        assert 'hx-target="#form-container"' in result
        assert (
            'hx-headers="{&quot;HX-Error-Target&quot;: &quot;#form-errors&quot;}"'
            in result
            or 'hx-headers=\'{"HX-Error-Target": "#form-errors"}\'' in result
            or '"HX-Error-Target": "#form-errors"' in result
        )


@pytest.mark.unit
class TestHtmxLazyLoad:
    """Test htmx_lazy_load filter."""

    def test_htmx_lazy_load_basic(self):
        """Test basic lazy loading."""
        result = htmx_lazy_load("/api/content")

        assert 'hx-get="/api/content"' in result
        assert 'hx-trigger="revealed once"' in result
        assert 'hx-indicator="this"' in result
        assert 'data-placeholder="Loading..."' in result

    def test_htmx_lazy_load_custom(self):
        """Test lazy loading with custom options."""
        result = htmx_lazy_load(
            "/api/heavy-content",
            placeholder="Loading heavy content...",
            trigger="intersect once",
            target="#content-area",
        )

        assert 'hx-get="/api/heavy-content"' in result
        assert 'hx-trigger="intersect once"' in result
        assert 'hx-target="#content-area"' in result
        assert 'data-placeholder="Loading heavy content..."' in result


@pytest.mark.unit
class TestHtmxInfiniteScroll:
    """Test htmx_infinite_scroll filter."""

    def test_htmx_infinite_scroll_basic(self):
        """Test basic infinite scroll."""
        result = htmx_infinite_scroll("/api/posts?page=2")

        assert 'hx-get="/api/posts?page=2"' in result
        assert 'hx-trigger="revealed"' in result
        assert 'hx-target="#infinite-container"' in result
        assert 'hx-swap="afterend"' in result

    def test_htmx_infinite_scroll_custom(self):
        """Test infinite scroll with custom container."""
        result = htmx_infinite_scroll(
            "/api/articles?page=3", container="#articles-list", swap="beforeend"
        )

        assert 'hx-get="/api/articles?page=3"' in result
        assert 'hx-target="#articles-list"' in result
        assert 'hx-swap="beforeend"' in result


@pytest.mark.unit
class TestHtmxSearch:
    """Test htmx_search filter."""

    def test_htmx_search_basic(self):
        """Test basic search functionality."""
        result = htmx_search("/api/search")

        assert 'hx-get="/api/search"' in result
        assert 'hx-trigger="keyup changed delay:300ms"' in result
        assert 'hx-target="#search-results"' in result
        assert 'hx-indicator="#search-loading"' in result

    def test_htmx_search_custom_debounce(self):
        """Test search with custom debounce."""
        result = htmx_search(
            "/api/search",
            debounce=500,
            target="#custom-results",
            include="closest form",
        )

        assert 'hx-get="/api/search"' in result
        assert 'hx-trigger="keyup changed delay:500ms"' in result
        assert 'hx-target="#custom-results"' in result
        assert 'hx-include="closest form"' in result


@pytest.mark.unit
class TestHtmxModal:
    """Test htmx_modal filter."""

    def test_htmx_modal_basic(self):
        """Test basic modal trigger."""
        result = htmx_modal("/modal/user/123")

        assert 'hx-get="/modal/user/123"' in result
        assert 'hx-target="#modal-container"' in result
        assert 'hx-swap="innerHTML"' in result

    def test_htmx_modal_custom(self):
        """Test modal with custom options."""
        result = htmx_modal(
            "/modal/confirmation",
            target="#custom-modal",
            swap="outerHTML",
            confirm="Are you sure?",
        )

        assert 'hx-get="/modal/confirmation"' in result
        assert 'hx-target="#custom-modal"' in result
        assert 'hx-swap="outerHTML"' in result
        assert 'hx-confirm="Are you sure?"' in result


@pytest.mark.unit
class TestHtmxImgSwap:
    """Test htmx_img_swap filter."""

    @patch("fastblocks.adapters.templates.filters.depends")
    def test_htmx_img_swap_with_adapter(self, mock_depends):
        """Test image swap with image adapter."""
        mock_images = Mock()
        mock_depends.get.return_value = mock_images

        result = htmx_img_swap(
            "product.jpg",
            transformations={"width": 300, "quality": 80},
            trigger="mouseenter once",
        )

        assert 'hx-get="/api/images/product.jpg/transform"' in result
        assert 'hx-target="this"' in result
        assert 'hx-swap="outerHTML"' in result
        assert 'hx-trigger="mouseenter once"' in result

    @patch("fastblocks.adapters.templates.filters.depends")
    def test_htmx_img_swap_no_adapter(self, mock_depends):
        """Test image swap without adapter."""
        mock_depends.get.return_value = None

        result = htmx_img_swap("image.jpg", trigger="click")

        assert 'hx-trigger="click"' in result


@pytest.mark.unit
class TestHtmxIconToggle:
    """Test htmx_icon_toggle filter."""

    def test_htmx_icon_toggle_basic(self):
        """Test basic icon toggle."""
        result = htmx_icon_toggle(
            "heart-filled", "heart-outline", post="/favorites/toggle/123"
        )

        assert 'hx-post="/favorites/toggle/123"' in result
        assert 'hx-swap="outerHTML"' in result
        assert 'hx-target="this"' in result
        assert 'data-icon-on="heart-filled"' in result
        assert 'data-icon-off="heart-outline"' in result

    def test_htmx_icon_toggle_custom(self):
        """Test icon toggle with custom options."""
        result = htmx_icon_toggle(
            "star-filled",
            "star-outline",
            patch="/ratings/toggle/456",
            target="closest .rating-container",
            confirm="Toggle rating?",
        )

        assert 'hx-patch="/ratings/toggle/456"' in result
        assert 'hx-target="closest .rating-container"' in result
        assert 'hx-confirm="Toggle rating?"' in result


@pytest.mark.unit
class TestHtmxWsConnect:
    """Test htmx_ws_connect filter."""

    def test_htmx_ws_connect_basic(self):
        """Test basic WebSocket connection."""
        result = htmx_ws_connect("/ws/notifications")

        assert 'hx-ext="ws"' in result
        assert 'ws-connect="/ws/notifications"' in result

    def test_htmx_ws_connect_with_listen(self):
        """Test WebSocket with event listening."""
        result = htmx_ws_connect(
            "/ws/chat/room123", listen="message-received", target="#messages"
        )

        assert 'hx-ext="ws"' in result
        assert 'hx-target="#messages"' in result
        assert 'ws-connect="/ws/chat/room123"' in result
        assert 'sse-listen="message-received"' in result


@pytest.mark.unit
class TestHtmxValidationFeedback:
    """Test htmx_validation_feedback filter."""

    def test_htmx_validation_feedback_basic(self):
        """Test basic validation feedback."""
        result = htmx_validation_feedback("email")

        assert 'hx-get="/validate/email"' in result
        assert 'hx-trigger="blur, keyup changed delay:500ms"' in result
        assert 'hx-target="#email-feedback"' in result
        assert 'hx-include="this"' in result

    def test_htmx_validation_feedback_custom(self):
        """Test validation feedback with custom URL."""
        result = htmx_validation_feedback(
            "username",
            validate_url="/api/validate/username",
            trigger="blur",
            target="#username-status",
        )

        assert 'hx-get="/api/validate/username"' in result
        assert 'hx-trigger="blur"' in result
        assert 'hx-target="#username-status"' in result


@pytest.mark.unit
class TestHtmxErrorContainer:
    """Test htmx_error_container filter."""

    def test_htmx_error_container_default(self):
        """Test default error container."""
        result = htmx_error_container()

        assert 'id="htmx-errors"' in result
        assert 'class="htmx-error-container"' in result
        assert 'role="alert"' in result

    def test_htmx_error_container_custom(self):
        """Test custom error container."""
        result = htmx_error_container("form-errors")

        assert 'id="form-errors"' in result
        assert 'class="htmx-error-container"' in result
        assert 'role="alert"' in result


@pytest.mark.unit
class TestHtmxRetryTrigger:
    """Test htmx_retry_trigger filter."""

    def test_htmx_retry_trigger_default(self):
        """Test default retry trigger."""
        result = htmx_retry_trigger()

        assert 'data-max-retries="3"' in result
        assert 'data-backoff="exponential"' in result

    def test_htmx_retry_trigger_custom(self):
        """Test custom retry trigger."""
        result = htmx_retry_trigger(max_retries=5, backoff="linear")

        assert 'data-max-retries="5"' in result
        assert 'data-backoff="linear"' in result


@pytest.mark.unit
class TestHtmxFiltersIntegration:
    """Test HTMX filters integration patterns."""

    def test_complete_form_pattern(self):
        """Test complete form with validation and error handling."""
        # Test form attributes
        form_attrs = htmx_form(
            "/users/create", target="#form-container", validation_target="#form-errors"
        )

        # Test validation field
        email_validation = htmx_validation_feedback(
            "email", validate_url="/validate/email"
        )

        # Test error container
        error_container = htmx_error_container("form-errors")

        assert 'hx-post="/users/create"' in form_attrs
        assert 'hx-target="#form-container"' in form_attrs
        assert "HX-Error-Target" in form_attrs and "#form-errors" in form_attrs

        assert 'hx-get="/validate/email"' in email_validation
        assert 'hx-target="#email-feedback"' in email_validation

        assert 'id="form-errors"' in error_container
        assert 'role="alert"' in error_container

    def test_infinite_scroll_with_search(self):
        """Test infinite scroll combined with search."""
        search_attrs = htmx_search(
            "/api/search", target="#search-results", debounce=250
        )

        scroll_attrs = htmx_infinite_scroll(
            "/api/posts?page=2", container="#search-results"
        )

        assert 'hx-trigger="keyup changed delay:250ms"' in search_attrs
        assert 'hx-target="#search-results"' in search_attrs

        assert 'hx-trigger="revealed"' in scroll_attrs
        assert 'hx-target="#search-results"' in scroll_attrs
        assert 'hx-swap="afterend"' in scroll_attrs
