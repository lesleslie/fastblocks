"""MCP resources for FastBlocks schemas, documentation, and patterns."""

import logging
from typing import Any

from acb.depends import depends

logger = logging.getLogger(__name__)


# Template Resources


async def get_template_syntax_reference() -> dict[str, Any]:
    """Get FastBlocks template syntax reference.

    Returns:
        Dict with comprehensive syntax documentation
    """
    return {
        "name": "FastBlocks Template Syntax Reference",
        "version": "0.16.0",
        "delimiters": {
            "variable": {
                "open": "[[",
                "close": "]]",
                "description": "Output variable values",
                "examples": [
                    "[[ user.name ]]",
                    "[[ items|length ]]",
                    "[[ price|currency ]]",
                ],
            },
            "statement": {
                "open": "[%",
                "close": "%]",
                "description": "Control flow and logic",
                "examples": [
                    "[% if user.is_active %]",
                    "[% for item in items %]",
                    "[% block content %]",
                ],
            },
            "comment": {
                "open": "[#",
                "close": "#]",
                "description": "Template comments (not rendered)",
                "examples": ["[# TODO: Add user avatar #]"],
            },
        },
        "common_patterns": {
            "conditionals": {
                "if": "[% if condition %]...[% endif %]",
                "if_else": "[% if condition %]...[% else %]...[% endif %]",
                "if_elif": "[% if cond1 %]...[% elif cond2 %]...[% else %]...[% endif %]",
            },
            "loops": {
                "for": "[% for item in items %]...[% endfor %]",
                "for_with_index": "[% for idx, item in enumerate(items) %]...[% endfor %]",
                "loop_controls": "loop.index, loop.index0, loop.first, loop.last",
            },
            "blocks": {
                "define": "[% block name %]...[% endblock %]",
                "override": "Child templates can override parent blocks",
                "super": "[[ super() ]] calls parent block content",
            },
            "includes": {
                "basic": "[% include 'path/to/template.html' %]",
                "with_context": "[% include 'template.html' with context %]",
                "with_vars": "[% include 'template.html' with {'var': value} %]",
            },
        },
        "best_practices": [
            "Use meaningful variable names",
            "Keep templates focused and small",
            "Extract reusable components",
            "Use blocks for layout inheritance",
            "Add comments for complex logic",
        ],
    }


async def get_available_filters() -> dict[str, Any]:
    """Get list of available template filters.

    Returns:
        Dict with filter documentation
    """
    return {
        "name": "FastBlocks Template Filters",
        "builtin_filters": {
            "string_filters": [
                {
                    "name": "upper",
                    "description": "Convert to uppercase",
                    "example": "[[ name|upper ]]",
                },
                {
                    "name": "lower",
                    "description": "Convert to lowercase",
                    "example": "[[ name|lower ]]",
                },
                {
                    "name": "title",
                    "description": "Title case",
                    "example": "[[ name|title ]]",
                },
                {
                    "name": "capitalize",
                    "description": "Capitalize first letter",
                    "example": "[[ name|capitalize ]]",
                },
                {
                    "name": "trim",
                    "description": "Remove whitespace",
                    "example": "[[ text|trim ]]",
                },
            ],
            "number_filters": [
                {
                    "name": "round",
                    "description": "Round to N decimal places",
                    "example": "[[ price|round(2) ]]",
                },
                {
                    "name": "abs",
                    "description": "Absolute value",
                    "example": "[[ number|abs ]]",
                },
            ],
            "list_filters": [
                {
                    "name": "length",
                    "description": "Get list/string length",
                    "example": "[[ items|length ]]",
                },
                {
                    "name": "first",
                    "description": "Get first item",
                    "example": "[[ items|first ]]",
                },
                {
                    "name": "last",
                    "description": "Get last item",
                    "example": "[[ items|last ]]",
                },
                {
                    "name": "join",
                    "description": "Join list with separator",
                    "example": "[[ tags|join(', ') ]]",
                },
            ],
            "formatting_filters": [
                {
                    "name": "date",
                    "description": "Format date",
                    "example": "[[ created_at|date('%Y-%m-%d') ]]",
                },
                {
                    "name": "currency",
                    "description": "Format as currency",
                    "example": "[[ price|currency ]]",
                },
                {
                    "name": "truncate",
                    "description": "Truncate string",
                    "example": "[[ text|truncate(100) ]]",
                },
            ],
        },
        "fastblocks_filters": {
            "htmx_filters": [
                {
                    "name": "htmx_attrs",
                    "description": "Generate HTMX attributes",
                    "example": "[[ attrs|htmx_attrs ]]",
                },
            ],
            "component_filters": [
                {
                    "name": "render_component",
                    "description": "Render HTMY component",
                    "example": "[[ render_component('user_card', {'name': 'John'}) ]]",
                },
            ],
        },
    }


async def get_htmy_component_catalog() -> dict[str, Any]:
    """Get catalog of available HTMY components.

    Returns:
        Dict with component catalog
    """
    try:
        htmy_adapter = await depends.get("htmy")
        if htmy_adapter is None:
            return {
                "success": False,
                "error": "HTMY adapter not available",
            }

        components = await htmy_adapter.discover_components()

        return {
            "name": "HTMY Component Catalog",
            "components": [
                {
                    "name": name,
                    "type": metadata.type.value,
                    "status": metadata.status.value,
                    "path": str(metadata.path),
                    "description": metadata.docstring,
                    "htmx_enabled": bool(metadata.htmx_attributes),
                }
                for name, metadata in components.items()
            ],
            "count": len(components),
            "component_types": {
                "basic": "Simple function-based components",
                "dataclass": "Dataclass-based components with type hints",
                "htmx": "HTMX-enabled interactive components",
                "composite": "Components composed of other components",
            },
        }

    except Exception as e:
        logger.error(f"Error getting component catalog: {e}")
        return {"success": False, "error": str(e)}


# Configuration Resources


async def get_adapter_schemas() -> dict[str, Any]:
    """Get configuration schemas for all adapters.

    Returns:
        Dict with adapter configuration schemas
    """
    try:
        from .discovery import AdapterDiscoveryServer

        discovery = AdapterDiscoveryServer()
        adapters = await discovery.discover_adapters()

        return {
            "name": "Adapter Configuration Schemas",
            "adapters": {
                name: {
                    "name": info.name,
                    "category": info.category,
                    "module_path": info.module_path,
                    "settings_class": info.settings_class,
                    "description": info.description,
                }
                for name, info in adapters.items()
            },
            "common_settings": {
                "enabled": {"type": "boolean", "default": True},
                "debug": {"type": "boolean", "default": False},
                "cache_enabled": {"type": "boolean", "default": True},
            },
        }

    except Exception as e:
        logger.error(f"Error getting adapter schemas: {e}")
        return {"success": False, "error": str(e)}


async def get_settings_documentation() -> dict[str, Any]:
    """Get FastBlocks settings documentation.

    Returns:
        Dict with settings structure and descriptions
    """
    return {
        "name": "FastBlocks Settings Documentation",
        "settings_files": {
            "app.yml": {
                "description": "Application configuration",
                "required_fields": {
                    "title": "Application title",
                    "domain": "Application domain",
                },
                "optional_fields": {
                    "description": "Application description",
                    "version": "Application version",
                },
            },
            "adapters.yml": {
                "description": "Adapter selection and configuration",
                "structure": {
                    "routes": "Route handler adapter (default, custom)",
                    "templates": "Template engine (jinja2, htmy)",
                    "auth": "Authentication adapter (basic, jwt, oauth)",
                    "sitemap": "Sitemap generator (asgi, native, cached)",
                },
            },
            "debug.yml": {
                "description": "Debug and development settings",
                "fields": {
                    "fastblocks": "Enable FastBlocks debug mode",
                    "production": "Production environment flag",
                },
            },
        },
        "environment_variables": {
            "FASTBLOCKS_ENV": "Environment name (development, staging, production)",
            "FASTBLOCKS_DEBUG": "Override debug mode",
            "FASTBLOCKS_SECRET_KEY": "Secret key for cryptography",
        },
    }


async def get_best_practices() -> dict[str, Any]:
    """Get FastBlocks best practices guide.

    Returns:
        Dict with best practices documentation
    """
    return {
        "name": "FastBlocks Best Practices",
        "architecture": {
            "separation_of_concerns": [
                "Keep routes thin, move logic to services",
                "Use adapters for external integrations",
                "Extract reusable components",
            ],
            "template_organization": [
                "Use variant-based organization (base, bulma, etc.)",
                "Keep blocks focused and small",
                "Use template inheritance for layouts",
            ],
            "component_design": [
                "Prefer dataclass components for type safety",
                "Use HTMX components for interactivity",
                "Document component props and behavior",
            ],
        },
        "performance": {
            "caching": [
                "Enable template caching in production",
                "Use Redis for distributed caching",
                "Cache database queries appropriately",
            ],
            "optimization": [
                "Minify CSS and JavaScript",
                "Use async operations throughout",
                "Enable Brotli compression",
            ],
        },
        "security": {
            "authentication": [
                "Use secure session management",
                "Implement CSRF protection",
                "Validate all user inputs",
            ],
            "templates": [
                "Auto-escape by default",
                "Use safe filters when needed",
                "Sanitize user-generated content",
            ],
        },
    }


# API Resources


async def get_route_definitions() -> dict[str, Any]:
    """Get route definitions from FastBlocks application.

    Returns:
        Dict with route information
    """
    try:
        # Try to get routes from ACB registry
        routes_adapter = await depends.get("routes")
        if routes_adapter is None:
            return {
                "success": False,
                "error": "Routes adapter not available",
            }

        # This would need actual route introspection
        # For now, return basic structure
        return {
            "name": "FastBlocks Route Definitions",
            "routes": [
                {
                    "path": "/",
                    "methods": ["GET"],
                    "handler": "index",
                    "description": "Home page",
                },
            ],
            "note": "Route definitions depend on application configuration",
        }

    except Exception as e:
        logger.error(f"Error getting route definitions: {e}")
        return {"success": False, "error": str(e)}


async def get_htmx_patterns() -> dict[str, Any]:
    """Get HTMX integration patterns for FastBlocks.

    Returns:
        Dict with HTMX pattern documentation
    """
    return {
        "name": "FastBlocks HTMX Integration Patterns",
        "common_patterns": {
            "inline_editing": {
                "description": "Click to edit inline",
                "template_example": """<div hx-get="/edit/[[ item.id ]]"
     hx-trigger="click"
     hx-target="this"
     hx-swap="outerHTML">
  [[ item.name ]]
</div>""",
            },
            "infinite_scroll": {
                "description": "Load more on scroll",
                "template_example": """<div hx-get="/items?page=[[ page + 1 ]]"
     hx-trigger="revealed"
     hx-swap="afterend">
</div>""",
            },
            "active_search": {
                "description": "Search as you type",
                "template_example": """<input type="text"
       hx-get="/search"
       hx-trigger="keyup changed delay:500ms"
       hx-target="#results">""",
            },
            "delete_confirmation": {
                "description": "Confirm before delete",
                "template_example": """<button hx-delete="/item/[[ item.id ]]"
        hx-confirm="Are you sure?"
        hx-target="closest .item"
        hx-swap="outerHTML swap:1s">
  Delete
</button>""",
            },
        },
        "response_helpers": {
            "htmx_trigger": "Trigger client-side events",
            "htmx_redirect": "Client-side redirect",
            "htmx_refresh": "Refresh current page",
            "htmx_response": "Custom HTMX response",
        },
    }


# Resource registration function


async def register_fastblocks_resources(server: Any) -> None:
    """Register all FastBlocks MCP resources with the server.

    Args:
        server: MCP server instance from ACB
    """
    try:
        from acb.mcp import register_resources  # type: ignore[attr-defined]

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
        await register_resources(server, resources)  # type: ignore[misc]

        logger.info(f"Registered {len(resources)} FastBlocks MCP resources")

    except Exception as e:
        logger.error(f"Failed to register MCP resources: {e}")
        raise
