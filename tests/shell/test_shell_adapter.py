"""Tests for FastBlocks admin shell."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

import pytest

from fastblocks.shell import FastBlocksShell


@pytest.fixture
def mock_app():
    """Create a mock FastBlocks app."""
    app = MagicMock()
    app.title = "Test App"
    app.user_middleware = []
    app.routes = []
    app.config = MagicMock()
    app.config.adapters = {"routes": "default", "templates": "jinja2", "auth": "basic"}
    return app


class TestFastBlocksShell:
    """Test FastBlocksShell class."""

    def test_init(self, mock_app):
        """Test shell initialization."""
        shell = FastBlocksShell(mock_app)

        assert shell.app == mock_app
        assert shell.namespace is not None
        assert "app" in shell.namespace
        assert "build" in shell.namespace
        assert "render" in shell.namespace
        assert "routes" in shell.namespace
        assert "auth" in shell.namespace

    def test_component_name(self, mock_app):
        """Test component name for session tracking."""
        shell = FastBlocksShell(mock_app)

        assert shell._get_component_name() == "fastblocks"

    def test_component_version(self, mock_app):
        """Test component version."""
        shell = FastBlocksShell(mock_app)

        version = shell._get_component_version()

        # Version should be a string
        assert isinstance(version, str)

    def test_adapters_info(self, mock_app):
        """Test adapters info."""
        shell = FastBlocksShell(mock_app)

        adapters = shell._get_adapters_info()

        assert isinstance(adapters, list)
        assert "web_framework" in adapters
        assert "ui_components" in adapters

    def test_build_helper(self, mock_app):
        """Test build helper."""
        shell = FastBlocksShell(mock_app)

        # Mock build_middleware_stack method
        mock_app.build_middleware_stack = MagicMock()

        result = shell.namespace["build"]()

        assert result["status"] == "success"
        assert "app_name" in result
        assert result["app_name"] == "Test App"

    def test_render_helper(self, mock_app):
        """Test render helper."""
        shell = FastBlocksShell(mock_app)

        # Mock templates
        mock_templates = MagicMock()
        mock_env = MagicMock()
        mock_env.loader = MagicMock()
        mock_env.loader.__class__.__name__ = "FileSystemLoader"
        mock_env.auto_reload = True
        mock_env.cache.capacity = 100
        mock_templates.env = mock_env
        mock_app.templates = mock_templates

        result = shell.namespace["render"]()

        assert result["status"] == "success"
        assert "templates" in result

    def test_routes_helper(self, mock_app):
        """Test routes helper."""
        shell = FastBlocksShell(mock_app)

        # Mock routes
        mock_route = MagicMock()
        mock_route.path = "/"
        mock_route.name = "index"
        mock_route.methods = ["GET"]
        mock_app.routes = [mock_route]

        routes = shell.namespace["routes"]()

        assert isinstance(routes, list)
        assert len(routes) == 1
        assert routes[0]["path"] == "/"

    def test_auth_helper(self, mock_app):
        """Test auth helper."""
        shell = FastBlocksShell(mock_app)

        auth = shell.namespace["auth"]

        assert isinstance(auth, dict)
        assert "enabled" in auth
        assert "type" in auth

    def test_banner(self, mock_app):
        """Test shell banner."""
        shell = FastBlocksShell(mock_app)

        banner = shell._get_banner()

        assert "FastBlocks Admin Shell" in banner
        assert "Version:" in banner
        assert "Session Tracking:" in banner
        assert "build()" in banner
        assert "render()" in banner
        assert "routes()" in banner

    def test_namespace_includes_async_helpers(self, mock_app):
        """Test that namespace includes asyncio and run helper."""
        shell = FastBlocksShell(mock_app)

        assert "asyncio" in shell.namespace
        assert "run" in shell.namespace
