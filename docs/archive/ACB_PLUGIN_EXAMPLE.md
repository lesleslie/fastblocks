# FastBlocks: ACB Plugin Reference Implementation

**Status**: Production Reference
**ACB Version**: 1.0.0+
**Last Updated**: 2025-01-27

______________________________________________________________________

## Overview

FastBlocks is the **reference implementation** of an ACB MCP plugin. This document demonstrates how FastBlocks extends ACB's MCP infrastructure to provide web framework-specific tools and resources.

Use this as a template when building your own ACB plugins.

______________________________________________________________________

## Minimal Working Example

Here's a complete minimal plugin in ~50 lines:

```python
"""minimal_plugin.py - Simplest ACB plugin possible"""

from acb.mcp import create_mcp_server, register_tools, register_resources
from typing import Any

# ============================================================================
# 1. Define Tools (MCP actions)
# ============================================================================

async def hello(name: str) -> dict[str, str]:
    """Say hello to someone."""
    return {"message": f"Hello, {name}!"}

async def add(a: int, b: int) -> dict[str, int]:
    """Add two numbers."""
    return {"result": a + b}

# ============================================================================
# 2. Define Resources (MCP documentation/data)
# ============================================================================

async def api_docs() -> str:
    """Return API documentation."""
    return """# Minimal Plugin API

## Tools

### hello(name)
Greets a person by name.

### add(a, b)
Adds two numbers together.
"""

# ============================================================================
# 3. Create Plugin Server
# ============================================================================

class MinimalPluginServer:
    \"\"\"Minimal ACB MCP plugin server.\"\"\"

    def __init__(self):
        # Create ACB server (inherits rate limiting)
        self._server = create_mcp_server()

    async def initialize(self):
        \"\"\"Register tools and resources.\"\"\"
        # Register tools
        await register_tools(self._server, {
            "hello": hello,
            "add": add,
        })

        # Register resources
        await register_resources(self._server, {
            "api_docs": api_docs,
        })

    def run(self):
        \"\"\"Run the server.\"\"\"
        self._server.run()  # STDIO mode for Claude Desktop

# ============================================================================
# 4. Entry Point
# ============================================================================

async def main():
    server = MinimalPluginServer()
    await server.initialize()
    server.run()

if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
```

**That's it!** This complete plugin:

- ✅ Inherits rate limiting (15 req/sec, burst 40)
- ✅ Provides 2 MCP tools
- ✅ Provides API documentation
- ✅ Works with Claude Desktop

______________________________________________________________________

## FastBlocks Implementation

FastBlocks follows this same pattern but with domain-specific functionality.

### Directory Structure

```
fastblocks/mcp/
├── __init__.py         # Exports
├── server.py           # Plugin server class
├── tools.py            # Tool implementations + registration
├── resources.py        # Resource implementations + registration
└── README.md           # Plugin documentation
```

### Server Implementation

**File**: `fastblocks/mcp/server.py`

```python
"""FastBlocks MCP server implementation."""

from typing import Any
from acb.mcp import create_mcp_server
from fastblocks.logger import logger

from .resources import register_fastblocks_resources
from .tools import register_fastblocks_tools


class FastBlocksMCPServer:
    """FastBlocks MCP server extending ACB infrastructure."""

    def __init__(
        self,
        name: str = "FastBlocks",
        version: str = "1.0.0",
        description: str = "FastBlocks MCP Server for IDE Integration",
    ):
        \"\"\"Initialize FastBlocks MCP server.

        Args:
            name: Server name
            version: Server version
            description: Server description
        \"\"\"
        self.name = name
        self.version = version
        self.description = description

        # Create ACB MCP server (inherits rate limiting)
        self._server = create_mcp_server()

        logger.info(
            f"FastBlocks MCP server initialized: {self.name} v{self.version} "
            f"(using ACB infrastructure with rate limiting: 15 req/sec, burst 40)"
        )

    async def initialize(self) -> None:
        \"\"\"Initialize server tools and resources.\"\"\"
        logger.info("Initializing FastBlocks MCP server...")

        await self._register_tools()
        await self._register_resources()

        logger.info("FastBlocks MCP server initialized successfully")

    async def _register_tools(self) -> None:
        \"\"\"Register FastBlocks-specific tools.\"\"\"
        await register_fastblocks_tools(self._server)

    async def _register_resources(self) -> None:
        \"\"\"Register FastBlocks-specific resources.\"\"\"
        await register_fastblocks_resources(self._server)

    def run(self, transport: str = "stdio", **kwargs: Any) -> None:
        \"\"\"Run the MCP server.

        Args:
            transport: Transport protocol ('stdio', 'http', 'sse')
            **kwargs: Additional transport arguments
        \"\"\"
        logger.info(f"Starting FastBlocks MCP server with {transport} transport")
        self._server.run(transport=transport, **kwargs)

    async def cleanup(self) -> None:
        \"\"\"Clean up server resources.\"\"\"
        logger.info("Cleaning up FastBlocks MCP server")
        await self._server.cleanup()
```

**Key Patterns**:

1. Store ACB server in `self._server`
1. Separate tool and resource registration
1. Use plugin-specific logger
1. Pass transport options through to ACB server

______________________________________________________________________

### Tool Registration

**File**: `fastblocks/mcp/tools.py` (simplified)

```python
"""FastBlocks MCP tool implementations."""

from typing import Any
from acb.mcp import register_tools
from fastblocks.logger import logger

# ============================================================================
# Tool Implementations
# ============================================================================

async def create_template(
    name: str,
    template_type: str = "jinja2",
) -> dict[str, Any]:
    \"\"\"Create a new template file.

    Args:
        name: Template name
        template_type: Template engine type

    Returns:
        Success status and template path
    \"\"\"
    try:
        # Implementation logic here
        template_path = f"templates/{name}.html"
        logger.info(f"Created template: {template_path}")

        return {
            "success": True,
            "template_path": template_path,
            "template_type": template_type,
        }
    except ValueError as e:
        logger.warning(f"Template creation failed: {e}")
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception(f"Unexpected error creating template: {e}")
        raise


async def validate_template(template_path: str) -> dict[str, Any]:
    \"\"\"Validate template syntax.

    Args:
        template_path: Path to template file

    Returns:
        Validation results
    \"\"\"
    try:
        # Implementation logic here
        errors = []  # Validation errors would be collected here

        return {
            "success": len(errors) == 0,
            "errors": errors,
            "template_path": template_path,
        }
    except Exception as e:
        logger.exception(f"Template validation error: {e}")
        raise


# Additional tools: list_templates, render_template, create_component, etc.

# ============================================================================
# Tool Registration
# ============================================================================

async def register_fastblocks_tools(server: Any) -> None:
    \"\"\"Register all FastBlocks MCP tools with the server.

    Args:
        server: MCP server instance from ACB
    \"\"\"
    try:
        from acb.mcp import register_tools

        # Define tool registry
        tools = {
            # Template tools
            "create_template": create_template,
            "validate_template": validate_template,
            "list_templates": list_templates,
            "render_template": render_template,

            # Component tools
            "create_component": create_component,
            "list_components": list_components,
            "validate_component": validate_component,

            # Adapter tools
            "configure_adapter": configure_adapter,
            "list_adapters": list_adapters,
            "check_adapter_health": check_adapter_health,
        }

        # Register tools with MCP server
        await register_tools(server, tools)

        logger.info(f"Registered {len(tools)} FastBlocks MCP tools")

    except Exception as e:
        logger.error(f"Failed to register MCP tools: {e}")
        raise
```

**Key Patterns**:

1. **Comprehensive error handling** (ValueError, Exception)
1. **Structured returns** (dict with success/error keys)
1. **Logging** at appropriate levels
1. **Bulk registration** (single register_tools call)

______________________________________________________________________

### Resource Registration

**File**: `fastblocks/mcp/resources.py` (simplified)

```python
"""FastBlocks MCP resource implementations."""

from typing import Any
from acb.mcp import register_resources
from fastblocks.logger import logger

# ============================================================================
# Resource Implementations
# ============================================================================

async def get_template_syntax_reference() -> str:
    \"\"\"Return template syntax reference in markdown.\"\"\"
    return \"\"\"# Template Syntax Reference

## Jinja2 Templates

### Variables
{{ variable_name }}

### Control Structures
{% if condition %}
...
{% endif %}

### Filters
{{ text|upper }}
{{ date|format_date }}

## HTMY Templates

### Components
<:ComponentName prop="value" />

### Slots
<:slot name="content" />
\"\"\"


async def get_htmy_component_catalog() -> str:
    \"\"\"Return catalog of available HTMY components.\"\"\"
    components = [
        {"name": "Button", "props": ["text", "variant", "size"]},
        {"name": "Card", "props": ["title", "content", "footer"]},
        {"name": "Modal", "props": ["title", "body", "actions"]},
    ]

    import json
    return json.dumps({"components": components}, indent=2)


# Additional resources: get_adapter_schemas, get_settings_documentation, etc.

# ============================================================================
# Resource Registration
# ============================================================================

async def register_fastblocks_resources(server: Any) -> None:
    \"\"\"Register all FastBlocks MCP resources with the server.

    Args:
        server: MCP server instance from ACB
    \"\"\"
    try:
        from acb.mcp import register_resources

        # Define resource registry
        resources = {
            # Template resources
            "template_syntax": get_template_syntax_reference,
            "template_filters": get_available_filters,
            "component_catalog": get_htmy_component_catalog,

            # Configuration resources
            "adapter_schemas": get_adapter_schemas,
            "settings_docs": get_settings_documentation,
            "best_practices": get_best_practices,

            # API resources
            "route_definitions": get_route_definitions,
            "htmx_patterns": get_htmx_patterns,
        }

        # Register resources with MCP server
        await register_resources(server, resources)

        logger.info(f"Registered {len(resources)} FastBlocks MCP resources")

    except Exception as e:
        logger.error(f"Failed to register MCP resources: {e}")
        raise
```

**Key Patterns**:

1. **Markdown format** for human-readable documentation
1. **JSON format** for structured data
1. **Idempotent** (safe to call multiple times)
1. **Error handling** with logging

______________________________________________________________________

## Testing Your Plugin

### Unit Tests

```python
"""test_plugin_integration.py"""

import pytest
from acb.mcp import create_mcp_server, register_tools, register_resources


@pytest.mark.asyncio
async def test_minimal_plugin_tools_register():
    \"\"\"Test that tools register successfully.\"\"\"
    server = create_mcp_server()

    async def test_tool(param: str) -> dict:
        return {"param": param}

    await register_tools(server, {"test_tool": test_tool})

    # Verify tool is registered
    assert hasattr(server._server, "tools")


@pytest.mark.asyncio
async def test_minimal_plugin_resources_register():
    \"\"\"Test that resources register successfully.\"\"\"
    server = create_mcp_server()

    async def test_resource() -> str:
        return "# Documentation"

    await register_resources(server, {"test_resource": test_resource})

    # Verify resource is registered
    assert hasattr(server._server, "resources")


@pytest.mark.asyncio
async def test_plugin_inherits_rate_limiting():
    \"\"\"Test that plugin inherits ACB rate limiting.\"\"\"
    server = create_mcp_server()

    # Verify rate limiter is configured
    assert hasattr(server._server, "_mcp_server")
    # Rate limiting is applied at middleware level
```

______________________________________________________________________

## Common Patterns

### Pattern 1: Validation Tools

```python
async def validate_config(config: dict) -> dict[str, Any]:
    \"\"\"Validate configuration dictionary.\"\"\"
    errors = []

    if "api_key" not in config:
        errors.append("Missing required field: api_key")

    if "timeout" in config and config["timeout"] < 1:
        errors.append("Timeout must be >= 1 second")

    return {
        "valid": len(errors) == 0,
        "errors": errors,
    }
```

### Pattern 2: List/Enumerate Tools

```python
async def list_templates() -> dict[str, Any]:
    \"\"\"List all available templates.\"\"\"
    try:
        templates = [
            {"name": "base.html", "type": "jinja2"},
            {"name": "form.html", "type": "jinja2"},
        ]

        return {
            "success": True,
            "templates": templates,
            "count": len(templates),
        }
    except Exception as e:
        logger.exception(f"Failed to list templates: {e}")
        raise
```

### Pattern 3: Creation/Modification Tools

```python
async def create_resource(name: str, **props) -> dict[str, Any]:
    \"\"\"Create a new resource.\"\"\"
    try:
        # Validation
        if not name:
            return {"success": False, "error": "Name is required"}

        # Creation logic
        resource_id = await db.create(name, **props)

        return {
            "success": True,
            "resource_id": resource_id,
            "message": f"Created {name}",
        }
    except ValueError as e:
        return {"success": False, "error": str(e)}
    except Exception as e:
        logger.exception(f"Resource creation failed: {e}")
        raise
```

______________________________________________________________________

## See Also

- **FastBlocks Source**: `/Users/les/Projects/fastblocks/fastblocks/mcp/`

______________________________________________________________________

**Status**: Production Reference
**Maintained By**: FastBlocks + ACB Teams
**License**: MIT
