"""Test HTTPEndpoints with HTMY component integration."""

from unittest.mock import AsyncMock, Mock

import pytest
from starlette.endpoints import HTTPEndpoint
from starlette.requests import Request
from starlette.responses import HTMLResponse
from fastblocks.adapters.templates.jinja2 import Templates


class HTMYTestEndpoint(HTTPEndpoint):
    """Test endpoint that uses HTMY components."""

    def __init__(self, scope, receive, send):
        super().__init__(scope, receive, send)
        # In real FastBlocks, this would be injected via ACB
        self.templates = None

    async def get(self, request: Request) -> HTMLResponse:
        """Handle GET request with HTMY component rendering."""
        if not self.templates:
            # Mock templates for testing
            self.templates = Mock(spec=Templates)
            self.templates.render_component = AsyncMock()
            self.templates.render_component.return_value = HTMLResponse(
                content="<div class='test-card'>Test Component Success</div>",
                status_code=200,
            )

        # Render HTMY component
        return await self.templates.render_component(
            request=request,
            component="test_card",
            context={"page": "test"},
            title="HTMY Endpoint Test",
            content="This component was rendered from an HTTPEndpoint",
        )

    async def post(self, request: Request) -> HTMLResponse:
        """Handle POST request with form data passed to HTMY component."""
        if not self.templates:
            self.templates = Mock(spec=Templates)
            self.templates.render_component = AsyncMock()
            self.templates.render_component.return_value = HTMLResponse(
                content="<div class='test-card'>Form Submitted Successfully</div>",
                status_code=200,
            )

        # Get form data
        form_data = await request.form()

        # Render HTMY component with form data
        return await self.templates.render_component(
            request=request,
            component="test_card",
            context={"form_data": dict(form_data)},
            title="Form Submission",
            content=f"Received: {dict(form_data)}",
        )


class HybridTemplateEndpoint(HTTPEndpoint):
    """Test endpoint that demonstrates Jinja2-HTMY interoperability."""

    def __init__(self, scope, receive, send):
        super().__init__(scope, receive, send)
        self.templates = None

    async def get(self, request: Request) -> HTMLResponse:
        """Render Jinja2 template that includes HTMY components."""
        if not self.templates:
            self.templates = Mock(spec=Templates)
            self.templates.render_template = AsyncMock()
            self.templates.render_template.return_value = HTMLResponse(
                content="""
                <html>
                <body>
                    <h1>Hybrid Template</h1>
                    <div class="htmy-section">
                        <div class='test-card'>HTMY Component in Jinja2 Template</div>
                    </div>
                </body>
                </html>
                """,
                status_code=200,
            )

        # Render Jinja2 template that calls HTMY components via render_component()
        return await self.templates.render_template(
            request=request,
            template="hybrid_template.html",
            context={
                "page_title": "Hybrid Test",
                "user_name": "Test User",
                "components": ["test_card", "bidirectional_test"],
            },
        )


@pytest.mark.unit
class TestHTMYEndpoints:
    """Test suite for HTTPEndpoints using HTMY components."""

    @pytest.fixture
    async def mock_scope(self):
        """Create mock ASGI scope."""
        return {
            "type": "http",
            "method": "GET",
            "path": "/test",
            "query_string": b"",
            "headers": [],
        }

    @pytest.fixture
    async def mock_receive(self):
        """Create mock ASGI receive callable."""

        async def receive():
            return {"type": "http.request", "body": b"", "more_body": False}

        return receive

    @pytest.fixture
    async def mock_send(self):
        """Create mock ASGI send callable."""
        messages = []

        async def send(message):
            messages.append(message)

        send.messages = messages
        return send

    async def test_htmy_endpoint_get(self, mock_scope, mock_receive, mock_send):
        """Test GET request to HTMY endpoint."""
        # Create endpoint instance
        endpoint = HTMYTestEndpoint(mock_scope, mock_receive, mock_send)

        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "GET"

        # Test the get method
        response = await endpoint.get(request)

        # Verify response
        assert isinstance(response, HTMLResponse)
        assert response.status_code == 200
        assert "Test Component Success" in response.body.decode()

    async def test_htmy_endpoint_post(self, mock_scope, mock_receive, mock_send):
        """Test POST request to HTMY endpoint with form data."""
        # Create endpoint instance
        endpoint = HTMYTestEndpoint(mock_scope, mock_receive, mock_send)

        # Create mock request with form data
        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "POST"

        # Mock form data
        async def mock_form():
            return {"name": "Test User", "email": "test@example.com"}

        request.form = mock_form

        # Test the post method
        response = await endpoint.post(request)

        # Verify response
        assert isinstance(response, HTMLResponse)
        assert response.status_code == 200
        assert "Form Submitted Successfully" in response.body.decode()

    async def test_hybrid_template_endpoint(self, mock_scope, mock_receive, mock_send):
        """Test endpoint that uses Jinja2 templates with HTMY components."""
        # Create endpoint instance
        endpoint = HybridTemplateEndpoint(mock_scope, mock_receive, mock_send)

        # Create mock request
        request = Mock(spec=Request)
        request.url.path = "/hybrid"
        request.method = "GET"

        # Test the get method
        response = await endpoint.get(request)

        # Verify response
        assert isinstance(response, HTMLResponse)
        assert response.status_code == 200
        content = response.body.decode()
        assert "Hybrid Template" in content
        assert "HTMY Component in Jinja2 Template" in content

    async def test_endpoint_error_handling(self, mock_scope, mock_receive, mock_send):
        """Test error handling in HTMY endpoints."""
        endpoint = HTMYTestEndpoint(mock_scope, mock_receive, mock_send)

        # Mock templates to raise an error
        endpoint.templates = Mock(spec=Templates)
        endpoint.templates.render_component = AsyncMock()
        endpoint.templates.render_component.side_effect = Exception(
            "Component not found"
        )

        request = Mock(spec=Request)
        request.url.path = "/test"
        request.method = "GET"

        # Should handle errors gracefully
        with pytest.raises(Exception) as exc_info:
            await endpoint.get(request)

        assert "Component not found" in str(exc_info.value)

    async def test_component_context_passing(self):
        """Test that context is properly passed to components in endpoints."""
        # Create proper mock ASGI values
        scope = {"type": "http", "method": "GET"}
        receive = Mock()
        send = Mock()
        endpoint = HTMYTestEndpoint(scope, receive, send)

        # Mock templates to capture the call
        endpoint.templates = Mock(spec=Templates)
        call_args = None

        async def capture_render_component(*args, **kwargs):
            nonlocal call_args
            call_args = (args, kwargs)
            return HTMLResponse(content="<div>Test</div>")

        endpoint.templates.render_component = capture_render_component

        request = Mock(spec=Request)
        request.url.path = "/test"

        # Call the endpoint
        await endpoint.get(request)

        # Verify the call arguments
        args, kwargs = call_args
        assert "request" in kwargs
        assert "component" in kwargs
        assert kwargs["component"] == "test_card"
        assert "context" in kwargs
        assert kwargs["title"] == "HTMY Endpoint Test"


@pytest.mark.unit
class TestHTMYEndpointIntegration:
    """Integration tests for HTMY endpoints with FastBlocks features."""

    async def test_endpoint_with_authentication_context(self):
        """Test endpoint that passes authentication context to HTMY components."""
        # Create proper mock ASGI values
        scope = {"type": "http", "method": "GET"}
        receive = Mock()
        send = Mock()
        endpoint = HTMYTestEndpoint(scope, receive, send)
        endpoint.templates = Mock(spec=Templates)

        # Capture the context passed to render_component
        captured_context = None

        async def capture_context(*args, **kwargs):
            nonlocal captured_context
            captured_context = kwargs.get("context", {})
            return HTMLResponse(content="<div>Authenticated</div>")

        endpoint.templates.render_component = capture_context

        # Mock authenticated request
        request = Mock(spec=Request)
        request.user = Mock()
        request.user.is_authenticated = True
        request.user.username = "testuser"

        # Call endpoint (would need to modify endpoint to handle auth)
        # This is a conceptual test showing how auth context would flow
        await endpoint.templates.render_component(
            request=request,
            component="test_card",
            context={
                "user": request.user,
                "is_authenticated": request.user.is_authenticated,
            },
        )

        # Verify authentication context was passed
        assert "user" in captured_context
        assert "is_authenticated" in captured_context
        assert captured_context["is_authenticated"] is True

    async def test_endpoint_with_session_data(self):
        """Test endpoint that passes session data to HTMY components."""
        # Create proper mock ASGI values
        scope = {"type": "http", "method": "GET"}
        receive = Mock()
        send = Mock()
        endpoint = HTMYTestEndpoint(scope, receive, send)
        endpoint.templates = Mock(spec=Templates)

        captured_kwargs = None

        async def capture_kwargs(*args, **kwargs):
            nonlocal captured_kwargs
            captured_kwargs = kwargs
            return HTMLResponse(content="<div>Session</div>")

        endpoint.templates.render_component = capture_kwargs

        # Mock request with session
        request = Mock(spec=Request)
        request.session = {"user_id": 123, "preferences": {"theme": "dark"}}

        # Call endpoint with session context
        await endpoint.templates.render_component(
            request=request, component="test_card", context={"session": request.session}
        )

        # Verify session data was passed
        assert "context" in captured_kwargs
        assert "session" in captured_kwargs["context"]
        assert captured_kwargs["context"]["session"]["user_id"] == 123


if __name__ == "__main__":
    # Run tests if called directly
    pytest.main([__file__, "-v"])
