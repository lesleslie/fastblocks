______________________________________________________________________

## id: 01K6JZ5GH2BYMGF7F2ZXVPWJKW

______________________________________________________________________

## id: 01K6J6B7PWDNS5YKMW7K99196D

______________________________________________________________________

## id: 01K6HP55A3GB9RDFT9GTG3HCBF

# FastBlocks MCP Server

> **FastBlocks Documentation**: [Main](../../README.md) | [Core Features](../../README.md) | [Actions](../actions/README.md) | [Adapters](../adapters/README.md)

Complete implementation of the Model Context Protocol (MCP) server for FastBlocks, enabling IDE/AI assistant integration.

## Overview

The FastBlocks MCP Server provides a standardized protocol for IDEs and AI assistants to interact with FastBlocks projects, offering:

- **Template Management**: Create, validate, list, and render templates
- **Component Management**: Scaffold, discover, and validate HTMY components
- **Adapter Configuration**: Configure and monitor FastBlocks adapters
- **Reference Documentation**: Access syntax, filters, patterns, and best practices

## Quick Start

### Starting the Server

```bash
# Start via CLI
python -m fastblocks mcp

# Or run directly
python -m fastblocks.mcp

# With custom port/host
python -m fastblocks mcp --port 8080 --host 0.0.0.0
```

### Programmatic Usage

```python
from fastblocks.mcp import create_fastblocks_mcp_server


async def main():
    server = await create_fastblocks_mcp_server()
    await server.start()


if __name__ == "__main__":
    import asyncio

    asyncio.run(main())
```

## MCP Tools

The server exposes 10+ MCP tools for interacting with FastBlocks:

### Template Tools

#### `create_template`

Create a new FastBlocks template.

**Parameters:**

- `name` (str): Template name (e.g., "user_card")
- `template_type` (str): Template engine ("jinja2" or "htmy")
- `variant` (str): Template variant/theme (default: "base")
- `content` (str): Optional custom template content

**Returns:**

```json
{
  "success": true,
  "path": "/templates/base/blocks/user_card.html",
  "type": "jinja2",
  "variant": "base"
}
```

#### `validate_template`

Validate a template for syntax errors.

**Parameters:**

- `template_path` (str): Path to template file

**Returns:**

```json
{
  "success": true|false,
  "errors": [
    {
      "line": 10,
      "column": 5,
      "message": "Unclosed tag",
      "severity": "error",
      "fix_suggestion": "Add closing tag"
    }
  ]
}
```

#### `list_templates`

List all available templates.

**Parameters:**

- `variant` (str, optional): Filter by variant

**Returns:**

```json
{
  "success": true,
  "templates": [
    {
      "name": "user_card",
      "path": "/templates/base/blocks/user_card.html",
      "variant": "base",
      "type": "jinja2"
    }
  ],
  "count": 1
}
```

#### `render_template`

Render a template with context for testing.

**Parameters:**

- `template_name` (str): Template name to render
- `context` (dict, optional): Template context variables
- `variant` (str): Template variant (default: "base")

**Returns:**

```json
{
  "success": true,
  "output": "<div>Rendered HTML</div>",
  "template": "user_card",
  "variant": "base"
}
```

### Component Tools

#### `create_component`

Create a new HTMY component.

**Parameters:**

- `name` (str): Component name
- `component_type` (str): Component type ("basic", "dataclass", "htmx", "composite")
- `props` (dict, optional): Component properties as {name: type}
- `htmx_enabled` (bool): Enable HTMX features

**Returns:**

```json
{
  "success": true,
  "path": "/templates/base/components/user_card.py",
  "name": "user_card",
  "type": "dataclass"
}
```

#### `list_components`

List all discovered HTMY components.

**Returns:**

```json
{
  "success": true,
  "components": [
    {
      "name": "user_card",
      "path": "/templates/base/components/user_card.py",
      "type": "dataclass",
      "status": "ready",
      "docstring": "User card component"
    }
  ],
  "count": 1
}
```

#### `validate_component`

Validate an HTMY component.

**Parameters:**

- `component_name` (str): Component name to validate

**Returns:**

```json
{
  "success": true,
  "component": "user_card",
  "type": "dataclass",
  "status": "ready",
  "path": "/templates/base/components/user_card.py",
  "dependencies": ["typing", "dataclasses"]
}
```

### Adapter Tools

#### `configure_adapter`

Configure a FastBlocks adapter.

**Parameters:**

- `adapter_name` (str): Adapter name (e.g., "templates", "auth")
- `settings` (dict): Adapter configuration settings

**Returns:**

```json
{
  "success": true,
  "adapter": "templates",
  "settings": {"cache_enabled": true}
}
```

#### `list_adapters`

List all available adapters.

**Parameters:**

- `category` (str, optional): Filter by category

**Returns:**

```json
{
  "success": true,
  "adapters": [
    {
      "name": "templates",
      "category": "templates",
      "module_path": "fastblocks.adapters.templates.jinja2",
      "description": "Jinja2 template adapter"
    }
  ],
  "count": 1,
  "categories": ["templates", "auth", "routes"]
}
```

#### `check_adapter_health`

Check health status of adapters.

**Parameters:**

- `adapter_name` (str, optional): Specific adapter to check

**Returns:**

```json
{
  "success": true,
  "checks": [
    {
      "adapter": "templates",
      "status": "healthy",
      "message": "All checks passed"
    }
  ],
  "healthy": 1,
  "unhealthy": 0
}
```

## MCP Resources

The server provides reference documentation as MCP resources:

### Template Resources

- **`template_syntax`**: Complete template syntax reference with delimiters, patterns, and examples
- **`template_filters`**: Available template filters (builtin and FastBlocks-specific)
- **`component_catalog`**: Catalog of all HTMY components

### Configuration Resources

- **`adapter_schemas`**: Configuration schemas for all adapters
- **`settings_docs`**: FastBlocks settings file documentation
- **`best_practices`**: Architecture, performance, and security best practices

### API Resources

- **`route_definitions`**: Application route definitions
- **`htmx_patterns`**: Common HTMX integration patterns

## Integration Examples

### VS Code Extension

```json
{
  "contributes": {
    "commands": [
      {
        "command": "fastblocks.createTemplate",
        "title": "FastBlocks: Create Template"
      }
    ]
  }
}
```

### AI Assistant Integration

```python
# Query available templates
templates = await mcp_client.call_tool("list_templates")

# Create new template based on user request
result = await mcp_client.call_tool(
    "create_template",
    {"name": "dashboard", "template_type": "jinja2", "variant": "bulma"},
)

# Get syntax reference
syntax = await mcp_client.get_resource("template_syntax")
```

## Architecture

### Server Components

```
fastblocks/mcp/
├── server.py           # FastMCP server implementation
├── tools.py            # MCP tool implementations
├── resources.py        # MCP resource definitions
├── discovery.py        # Adapter discovery system
├── health.py           # Health check system
├── registry.py         # Adapter registry
└── __main__.py         # CLI entry point
```

### ACB Integration

The MCP server leverages ACB's FastMCP infrastructure:

- **`create_mcp_server()`**: Creates MCP protocol server
- **`register_tools()`**: Registers callable tools
- **`register_resources()`**: Registers documentation resources

### Graceful Degradation

The server gracefully degrades when ACB MCP support is unavailable:

```python
from acb import HAS_MCP

if not HAS_MCP:
    logger.warning("MCP support not available")
    return
```

## Testing

Run the comprehensive MCP server test suite:

```bash
# Run all MCP tests
python -m pytest tests/mcp/test_mcp_server.py -v

# Run specific test class
python -m pytest tests/mcp/test_mcp_server.py::TestMCPTools -v

# Run with coverage
python -m pytest tests/mcp/test_mcp_server.py --cov=fastblocks.mcp
```

## Troubleshooting

### Server Won't Start

**Issue**: `ModuleNotFoundError: No module named 'acb.mcp'`

**Solution**: Ensure ACB >= 0.23.0 is installed:

```bash
uv add 'acb>=0.23.0'
```

### Tools Return Errors

**Issue**: Tools return `{"success": false, "error": "..."}`

**Solution**: Check that you're in a FastBlocks project directory with proper structure:

```
project/
├── templates/
├── settings/
└── main.py
```

### Import Errors

**Issue**: `AttributeError: module 'acb' has no attribute 'create_mcp_server'`

**Solution**: ACB MCP support is optional. The server will gracefully degrade if unavailable.

## Future Enhancements

Planned improvements for the MCP server:

1. **Language Server Protocol (LSP)** integration for template editing
1. **Hot Reload** support for template changes
1. **Debugging Tools** for template rendering
1. **Performance Profiling** via MCP
1. **Project Scaffolding** templates

## Related Documentation

- [FastBlocks README](../../README.md) - Project overview
- [ACB Documentation](https://github.com/lesleslie/acb) - ACB framework
- [MCP Specification](https://modelcontextprotocol.io) - MCP protocol details

## Support

For issues, feature requests, or questions:

- **GitHub Issues**: https://github.com/lesleslie/fastblocks/issues
- **Discussions**: https://github.com/lesleslie/fastblocks/discussions
