"""Integration tests for FastBlocks admin shell."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest


@pytest.mark.integration
def test_shell_with_mock_app():
    """Test shell initialization with a mock FastBlocks app."""
    from fastblocks.shell import FastBlocksShell

    # Create a mock app
    app = MagicMock()
    app.title = "Test App"
    app.user_middleware = []
    app.routes = []
    app.config = MagicMock()
    app.config.adapters = {"routes": "default", "templates": "jinja2"}

    # Initialize shell
    shell = FastBlocksShell(app)

    # Verify shell is initialized
    assert shell.app == app
    assert shell.namespace is not None
    assert "app" in shell.namespace
    assert "build" in shell.namespace
    assert "render" in shell.namespace
    assert "routes" in shell.namespace
    assert "auth" in shell.namespace

    # Verify component metadata
    assert shell._get_component_name() == "fastblocks"
    assert shell._get_component_version() != "unknown"

    # Verify adapters info
    adapters = shell._get_adapters_info()
    assert "web_framework" in adapters
    assert "ui_components" in adapters

    # Verify banner
    banner = shell._get_banner()
    assert "FastBlocks Admin Shell" in banner
    assert "Session Tracking:" in banner
    assert "build()" in banner
    assert "render()" in banner
    assert "routes()" in banner


@pytest.mark.integration
def test_shell_helpers_execution():
    """Test shell helper functions execute correctly."""
    from fastblocks.shell import FastBlocksShell

    # Create a mock app with templates
    app = MagicMock()
    app.title = "Test App"
    app.user_middleware = []
    app.routes = []

    # Mock templates
    mock_templates = MagicMock()
    mock_env = MagicMock()
    mock_env.loader = MagicMock()
    mock_env.loader.__class__.__name__ = "FileSystemLoader"
    mock_env.auto_reload = True
    mock_env.cache.capacity = 100
    mock_templates.env = mock_env
    app.templates = mock_templates

    # Mock build method
    app.build_middleware_stack = MagicMock()

    app.config = MagicMock()
    app.config.adapters = {"routes": "default", "templates": "jinja2", "auth": "basic"}

    # Initialize shell
    shell = FastBlocksShell(app)

    # Test build helper
    build_result = shell.namespace["build"]()
    assert build_result["status"] == "success"
    assert "app_name" in build_result

    # Test render helper
    render_result = shell.namespace["render"]()
    assert render_result["status"] == "success"
    assert "templates" in render_result

    # Test routes helper
    routes_result = shell.namespace["routes"]()
    assert isinstance(routes_result, list)

    # Test auth helper
    auth_result = shell.namespace["auth"]
    assert isinstance(auth_result, dict)
    assert "enabled" in auth_result
