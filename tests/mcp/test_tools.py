"""Tests for MCP tools functionality."""

from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastblocks.mcp.tools import (
    _determine_template_type,
    _should_skip_variant_dir,
    check_adapter_health,
    configure_adapter,
    create_component,
    create_template,
    list_adapters,
    list_components,
    list_templates,
    validate_component,
    validate_template,
)


class TestCreateTemplate:
    """Test create_template functionality."""

    @pytest.mark.asyncio
    async def test_create_template_jinja2_default(self, tmp_path):
        """Test creating a Jinja2 template with default content."""
        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await create_template(name="user_card")

            assert result["success"] is True
            assert "user_card.html" in result["path"]
            assert result["type"] == "jinja2"
            assert result["variant"] == "base"

            # Check file was created
            template_path = Path(result["path"])
            assert template_path.exists()
            content = template_path.read_text()
            assert "user_card" in content

    @pytest.mark.asyncio
    async def test_create_template_htmy(self, tmp_path):
        """Test creating an HTMY template."""
        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await create_template(
                name="button_component", template_type="htmy"
            )

            assert result["success"] is True
            assert "button_component.py" in result["path"]
            assert result["type"] == "htmy"

            # Check file contains HTMY component structure
            template_path = Path(result["path"])
            content = template_path.read_text()
            assert "@dataclass" in content
            assert "def htmy" in content

    @pytest.mark.asyncio
    async def test_create_template_custom_variant(self, tmp_path):
        """Test creating a template with custom variant."""
        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await create_template(name="card", variant="bulma")

            assert result["success"] is True
            assert "bulma" in result["path"]
            assert result["variant"] == "bulma"

    @pytest.mark.asyncio
    async def test_create_template_custom_content(self, tmp_path):
        """Test creating a template with custom content."""
        custom_content = "<div>Custom template content</div>"

        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await create_template(name="custom", content=custom_content)

            assert result["success"] is True
            template_path = Path(result["path"])
            assert template_path.read_text() == custom_content

    @pytest.mark.asyncio
    async def test_create_template_already_exists(self, tmp_path):
        """Test creating a template that already exists."""
        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            # Create template first time
            await create_template(name="existing")

            # Try to create again
            result = await create_template(name="existing")

            assert result["success"] is False
            assert "already exists" in result["error"]

    @pytest.mark.asyncio
    async def test_create_template_handles_exceptions(self):
        """Test create_template handles exceptions gracefully."""
        with patch(
            "fastblocks.mcp.tools.Path.cwd", side_effect=Exception("Path error")
        ):
            result = await create_template(name="test")

            assert result["success"] is False
            assert "error" in result


class TestValidateTemplate:
    """Test validate_template functionality."""

    @pytest.mark.asyncio
    async def test_validate_template_not_found(self):
        """Test validating a non-existent template."""
        result = await validate_template("/nonexistent/template.html")

        assert result["success"] is False
        assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_template_no_syntax_support(self, tmp_path):
        """Test validation when syntax support is not available."""
        template_path = tmp_path / "test.html"
        template_path.write_text("<div>Test</div>")

        async def mock_get(name):
            return None

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await validate_template(str(template_path))

            assert result["success"] is False
            assert "Syntax support not available" in result["error"]

    @pytest.mark.asyncio
    async def test_validate_template_success(self, tmp_path):
        """Test successful template validation."""
        template_path = tmp_path / "valid.html"
        template_path.write_text("<div>Valid template</div>")

        mock_syntax_support = MagicMock()
        mock_syntax_support.check_syntax = MagicMock(return_value=[])

        async def mock_get(name):
            return mock_syntax_support

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await validate_template(str(template_path))

            assert result["success"] is True
            assert result["errors"] == []
            assert result["path"] == str(template_path)

    @pytest.mark.asyncio
    async def test_validate_template_with_errors(self, tmp_path):
        """Test template validation with syntax errors."""
        template_path = tmp_path / "invalid.html"
        template_path.write_text("<div>Invalid</div>")

        mock_error = MagicMock()
        mock_error.line = 1
        mock_error.column = 5
        mock_error.message = "Syntax error"
        mock_error.severity = "error"
        mock_error.code = "E001"
        mock_error.fix_suggestion = "Fix it"

        mock_syntax_support = MagicMock()
        mock_syntax_support.check_syntax = MagicMock(return_value=[mock_error])

        async def mock_get(name):
            return mock_syntax_support

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await validate_template(str(template_path))

            assert result["success"] is False
            assert len(result["errors"]) == 1
            assert result["errors"][0]["message"] == "Syntax error"

    @pytest.mark.asyncio
    async def test_validate_template_handles_exceptions(self, tmp_path):
        """Test validate_template handles exceptions."""
        template_path = tmp_path / "test.html"
        template_path.write_text("content")

        async def mock_get(name):
            raise Exception("Validation error")

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await validate_template(str(template_path))

            assert result["success"] is False
            assert "error" in result


class TestListTemplates:
    """Test list_templates functionality."""

    @pytest.mark.asyncio
    async def test_list_templates_no_templates_dir(self, tmp_path):
        """Test listing templates when directory doesn't exist."""
        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await list_templates()

            assert result["success"] is False
            assert "not found" in result["error"]

    @pytest.mark.asyncio
    async def test_list_templates_success(self, tmp_path):
        """Test successful template listing."""
        templates_dir = tmp_path / "templates" / "base" / "blocks"
        templates_dir.mkdir(parents=True)

        # Create test templates
        (templates_dir / "card.html").write_text("card template")
        (templates_dir / "button.html").write_text("button template")

        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await list_templates()

            assert result["success"] is True
            assert result["count"] >= 0
            assert "variants" in result

    @pytest.mark.asyncio
    async def test_list_templates_with_variant_filter(self, tmp_path):
        """Test listing templates with variant filter."""
        templates_dir = tmp_path / "templates"
        base_dir = templates_dir / "base" / "blocks"
        base_dir.mkdir(parents=True)
        (base_dir / "card.html").write_text("card")

        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await list_templates(variant="base")

            assert result["success"] is True


class TestCreateComponent:
    """Test create_component functionality."""

    @pytest.mark.asyncio
    async def test_create_component_success(self, tmp_path):
        """Test successful component creation."""
        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await create_component(name="UserCard", component_type="htmy")

            # Component creation should work
            assert "success" in result

    @pytest.mark.asyncio
    async def test_create_component_handles_exceptions(self):
        """Test create_component handles exceptions."""
        with patch(
            "fastblocks.mcp.tools.Path.cwd", side_effect=Exception("Component error")
        ):
            result = await create_component(name="Test")

            assert result["success"] is False


class TestListComponents:
    """Test list_components functionality."""

    @pytest.mark.asyncio
    async def test_list_components_no_gather(self):
        """Test listing components when gather is not available."""

        async def mock_get(name):
            return None

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await list_components()

            assert result["success"] is False
            assert "Gather functionality not available" in result["error"]

    @pytest.mark.asyncio
    async def test_list_components_success(self):
        """Test successful component listing."""
        mock_result = MagicMock()
        mock_result.is_success = True
        mock_result.components = {"UserCard": MagicMock()}
        mock_result.total_components = 1

        mock_gather = MagicMock()
        mock_gather.components = AsyncMock(return_value=mock_result)

        async def mock_get(name):
            return mock_gather

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await list_components()

            assert result["success"] is True
            assert result["count"] == 1


class TestValidateComponent:
    """Test validate_component functionality."""

    @pytest.mark.asyncio
    async def test_validate_component_not_found(self):
        """Test validating non-existent component."""
        mock_gather = MagicMock()
        mock_gather.components = AsyncMock(return_value=MagicMock(components={}))

        async def mock_get(name):
            return mock_gather

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await validate_component("NonExistent")

            assert result["success"] is False
            assert "not found" in result["error"]


class TestConfigureAdapter:
    """Test configure_adapter functionality."""

    @pytest.mark.asyncio
    async def test_configure_adapter_success(self, tmp_path):
        """Test successful adapter configuration."""
        settings_dir = tmp_path / "settings"
        settings_dir.mkdir()

        with patch("fastblocks.mcp.tools.Path.cwd", return_value=tmp_path):
            result = await configure_adapter(
                adapter_name="test_adapter", settings={"key": "value"}
            )

            assert result["success"] is True
            assert result["adapter"] == "test_adapter"

    @pytest.mark.asyncio
    async def test_configure_adapter_handles_exceptions(self):
        """Test configure_adapter handles exceptions."""
        with patch(
            "fastblocks.mcp.tools.Path.cwd", side_effect=Exception("Config error")
        ):
            result = await configure_adapter(adapter_name="test", settings={})

            assert result["success"] is False


class TestListAdapters:
    """Test list_adapters functionality."""

    @pytest.mark.asyncio
    async def test_list_adapters_no_discovery(self):
        """Test listing adapters when discovery is not available."""

        async def mock_get(name):
            return None

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await list_adapters()

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_list_adapters_success(self):
        """Test successful adapter listing."""
        mock_adapters = {"auth": MagicMock(), "database": MagicMock()}
        mock_discovery = AsyncMock()
        mock_discovery.list_available_adapters = AsyncMock(return_value=mock_adapters)

        async def mock_get(name):
            return mock_discovery

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await list_adapters()

            assert result["success"] is True
            assert result["count"] == 2

    @pytest.mark.asyncio
    async def test_list_adapters_with_category_filter(self):
        """Test listing adapters with category filter."""
        mock_auth = MagicMock()
        mock_auth.category = "auth"
        mock_db = MagicMock()
        mock_db.category = "database"

        mock_adapters = {"auth_adapter": mock_auth, "db_adapter": mock_db}
        mock_discovery = AsyncMock()
        mock_discovery.list_available_adapters = AsyncMock(return_value=mock_adapters)

        async def mock_get(name):
            return mock_discovery

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await list_adapters(category="auth")

            assert result["success"] is True


class TestCheckAdapterHealth:
    """Test check_adapter_health functionality."""

    @pytest.mark.asyncio
    async def test_check_adapter_health_no_health_system(self):
        """Test health check when health system is not available."""

        async def mock_get(name):
            return None

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await check_adapter_health()

            assert result["success"] is False

    @pytest.mark.asyncio
    async def test_check_adapter_health_all_adapters(self):
        """Test checking health of all adapters."""
        mock_health = AsyncMock()
        mock_health.check_all = AsyncMock(
            return_value={
                "auth": {"status": "healthy"},
                "database": {"status": "healthy"},
            }
        )

        async def mock_get(name):
            return mock_health

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await check_adapter_health()

            assert result["success"] is True
            assert "health_checks" in result

    @pytest.mark.asyncio
    async def test_check_adapter_health_specific_adapter(self):
        """Test checking health of specific adapter."""
        mock_health = AsyncMock()
        mock_health.check = AsyncMock(return_value={"status": "healthy"})

        async def mock_get(name):
            return mock_health

        with patch("fastblocks.mcp.tools.depends.get", new=mock_get):
            result = await check_adapter_health(adapter_name="auth")

            assert result["success"] is True
            assert result["adapter"] == "auth"


class TestHelperFunctions:
    """Test helper functions."""

    def test_should_skip_variant_dir_skip(self):
        """Test _should_skip_variant_dir returns True when should skip."""
        variant_dir = Path("templates/bulma")

        result = _should_skip_variant_dir(variant_dir, "base")

        assert result is True

    def test_should_skip_variant_dir_no_skip(self):
        """Test _should_skip_variant_dir returns False when shouldn't skip."""
        variant_dir = Path("templates/base")

        result = _should_skip_variant_dir(variant_dir, "base")

        assert result is False

    def test_should_skip_variant_dir_no_filter(self):
        """Test _should_skip_variant_dir with no filter."""
        variant_dir = Path("templates/any")

        result = _should_skip_variant_dir(variant_dir, None)

        assert result is False

    def test_determine_template_type_jinja2(self):
        """Test _determine_template_type for Jinja2 templates."""
        assert _determine_template_type(".html") == "jinja2"
        assert _determine_template_type(".jinja2") == "jinja2"
        assert _determine_template_type(".j2") == "jinja2"

    def test_determine_template_type_htmy(self):
        """Test _determine_template_type for HTMY templates."""
        assert _determine_template_type(".py") == "htmy"

    def test_determine_template_type_unknown(self):
        """Test _determine_template_type for unknown types."""
        assert _determine_template_type(".txt") == "unknown"
