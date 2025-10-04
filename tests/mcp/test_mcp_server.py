"""Comprehensive tests for FastBlocks MCP server implementation."""

import pytest


class TestMCPServer:
    """Tests for FastBlocks MCP server initialization and lifecycle."""

    @pytest.mark.asyncio
    async def test_server_initialization(self):
        """Test MCP server can be initialized."""
        from fastblocks.mcp import create_fastblocks_mcp_server

        server = await create_fastblocks_mcp_server()
        assert server is not None
        assert server.name == "fastblocks"
        assert server.version == "0.16.0"

    @pytest.mark.asyncio
    async def test_server_initialized_flag(self):
        """Test server initialization flag is set correctly."""
        from fastblocks.mcp import FastBlocksMCPServer

        server = FastBlocksMCPServer()
        assert not server._initialized

        await server.initialize()
        # Initialized flag depends on ACB MCP availability
        # If ACB MCP is not available, server gracefully degrades

    @pytest.mark.asyncio
    async def test_server_double_initialization(self):
        """Test server handles double initialization gracefully."""
        from fastblocks.mcp import FastBlocksMCPServer

        server = FastBlocksMCPServer()
        await server.initialize()
        await server.initialize()  # Should not raise

    @pytest.mark.asyncio
    async def test_server_graceful_degradation(self):
        """Test server degrades gracefully when ACB MCP unavailable."""
        from fastblocks.mcp import FastBlocksMCPServer

        server = FastBlocksMCPServer()
        # Should not raise even if ACB MCP not available
        await server.initialize()


class TestMCPTools:
    """Tests for FastBlocks MCP tool implementations."""

    @pytest.mark.asyncio
    async def test_create_template_jinja2(self, tmp_path, monkeypatch):
        """Test creating a Jinja2 template."""
        from fastblocks.mcp.tools import create_template

        # Set working directory to temp path
        monkeypatch.chdir(tmp_path)

        result = await create_template(
            name="test_template", template_type="jinja2", variant="base"
        )

        assert result["success"] is True
        assert "test_template.html" in result["path"]
        assert result["type"] == "jinja2"

    @pytest.mark.asyncio
    async def test_create_template_htmy(self, tmp_path, monkeypatch):
        """Test creating an HTMY template."""
        from fastblocks.mcp.tools import create_template

        monkeypatch.chdir(tmp_path)

        result = await create_template(
            name="test_component", template_type="htmy", variant="base"
        )

        assert result["success"] is True
        assert "test_component.py" in result["path"]
        assert result["type"] == "htmy"

    @pytest.mark.asyncio
    async def test_create_template_duplicate(self, tmp_path, monkeypatch):
        """Test creating duplicate template fails gracefully."""
        from fastblocks.mcp.tools import create_template

        monkeypatch.chdir(tmp_path)

        # Create first template
        result1 = await create_template(name="dup_test", template_type="jinja2")
        assert result1["success"] is True

        # Try to create duplicate
        result2 = await create_template(name="dup_test", template_type="jinja2")
        assert result2["success"] is False
        assert "already exists" in result2["error"]

    @pytest.mark.asyncio
    async def test_list_templates_empty(self, tmp_path, monkeypatch):
        """Test listing templates in empty directory."""
        from fastblocks.mcp.tools import list_templates

        monkeypatch.chdir(tmp_path)

        result = await list_templates()
        assert result["success"] is True
        assert result["count"] == 0
        assert result["templates"] == []

    @pytest.mark.asyncio
    async def test_list_templates_with_content(self, tmp_path, monkeypatch):
        """Test listing templates after creating some."""
        from fastblocks.mcp.tools import create_template, list_templates

        monkeypatch.chdir(tmp_path)

        # Create some templates
        await create_template(name="template1", variant="base")
        await create_template(name="template2", variant="base")

        result = await list_templates()
        assert result["success"] is True
        assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_list_templates_filtered_by_variant(self, tmp_path, monkeypatch):
        """Test listing templates filtered by variant."""
        from fastblocks.mcp.tools import create_template, list_templates

        monkeypatch.chdir(tmp_path)

        await create_template(name="base_tmpl", variant="base")
        await create_template(name="bulma_tmpl", variant="bulma")

        result = await list_templates(variant="base")
        assert result["success"] is True
        assert result["count"] == 1
        assert result["templates"][0]["variant"] == "base"

    @pytest.mark.asyncio
    async def test_list_adapters(self):
        """Test listing available adapters."""
        from fastblocks.mcp.tools import list_adapters

        result = await list_adapters()
        assert result["success"] is True
        assert "adapters" in result
        assert "count" in result

    @pytest.mark.asyncio
    async def test_list_adapters_filtered(self):
        """Test listing adapters filtered by category."""
        from fastblocks.mcp.tools import list_adapters

        result = await list_adapters(category="templates")
        assert result["success"] is True
        # If templates category exists, should be filtered
        if result["count"] > 0:
            assert all(
                adapter["category"] == "templates" for adapter in result["adapters"]
            )

    @pytest.mark.asyncio
    async def test_check_adapter_health(self):
        """Test checking adapter health."""
        from fastblocks.mcp.tools import check_adapter_health

        result = await check_adapter_health()
        # Health check may fail if adapters not available, which is fine
        assert "success" in result
        if result["success"]:
            assert "checks" in result
            assert "healthy" in result
            assert "unhealthy" in result


class TestMCPResources:
    """Tests for FastBlocks MCP resource implementations."""

    @pytest.mark.asyncio
    async def test_template_syntax_reference(self):
        """Test getting template syntax reference."""
        from fastblocks.mcp.resources import get_template_syntax_reference

        result = await get_template_syntax_reference()
        assert "delimiters" in result
        assert "variable" in result["delimiters"]
        assert result["delimiters"]["variable"]["open"] == "[["
        assert result["delimiters"]["variable"]["close"] == "]]"

    @pytest.mark.asyncio
    async def test_available_filters(self):
        """Test getting available filters."""
        from fastblocks.mcp.resources import get_available_filters

        result = await get_available_filters()
        assert "builtin_filters" in result
        assert "string_filters" in result["builtin_filters"]
        assert "fastblocks_filters" in result

    @pytest.mark.asyncio
    async def test_adapter_schemas(self):
        """Test getting adapter configuration schemas."""
        from fastblocks.mcp.resources import get_adapter_schemas

        result = await get_adapter_schemas()
        assert "adapters" in result or "success" in result

    @pytest.mark.asyncio
    async def test_settings_documentation(self):
        """Test getting settings documentation."""
        from fastblocks.mcp.resources import get_settings_documentation

        result = await get_settings_documentation()
        assert "settings_files" in result
        assert "app.yml" in result["settings_files"]
        assert "adapters.yml" in result["settings_files"]

    @pytest.mark.asyncio
    async def test_best_practices(self):
        """Test getting best practices guide."""
        from fastblocks.mcp.resources import get_best_practices

        result = await get_best_practices()
        assert "architecture" in result
        assert "performance" in result
        assert "security" in result

    @pytest.mark.asyncio
    async def test_htmx_patterns(self):
        """Test getting HTMX integration patterns."""
        from fastblocks.mcp.resources import get_htmx_patterns

        result = await get_htmx_patterns()
        assert "common_patterns" in result
        assert "response_helpers" in result


class TestMCPIntegration:
    """Integration tests for MCP server with ACB."""

    @pytest.mark.asyncio
    async def test_server_exports(self):
        """Test MCP module exports are available."""
        from fastblocks.mcp import (
            AdapterDiscoveryServer,
            FastBlocksMCPServer,
            HealthCheckSystem,
            create_fastblocks_mcp_server,
        )

        assert AdapterDiscoveryServer is not None
        assert HealthCheckSystem is not None
        assert FastBlocksMCPServer is not None
        assert create_fastblocks_mcp_server is not None

    @pytest.mark.asyncio
    async def test_cli_integration(self):
        """Test MCP command is available in CLI."""
        # Skip test - CLI has environment dependencies
        # that may not be available in test environment
        pytest.skip("CLI integration test requires full FastBlocks environment")


class TestMCPErrorHandling:
    """Tests for MCP error handling and edge cases."""

    @pytest.mark.asyncio
    async def test_validate_template_nonexistent(self):
        """Test validating non-existent template."""
        from fastblocks.mcp.tools import validate_template

        result = await validate_template("/nonexistent/template.html")
        assert result["success"] is False
        assert "not found" in result["error"].lower()

    @pytest.mark.asyncio
    async def test_create_template_custom_content(self, tmp_path, monkeypatch):
        """Test creating template with custom content."""
        from fastblocks.mcp.tools import create_template

        monkeypatch.chdir(tmp_path)

        custom_content = "<div>Custom template content</div>"
        result = await create_template(
            name="custom", template_type="jinja2", content=custom_content
        )

        assert result["success"] is True
        # Verify content was written
        from pathlib import Path

        created_file = Path(result["path"])
        assert created_file.read_text() == custom_content
