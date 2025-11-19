"""MCP tools for FastBlocks template, component, and adapter management."""

import logging
import operator
from pathlib import Path
from typing import Any

from acb.depends import depends

from .discovery import AdapterDiscoveryServer
from .health import HealthCheckSystem

logger = logging.getLogger(__name__)


# Template Management Tools


async def create_template(
    name: str,
    template_type: str = "jinja2",
    variant: str = "base",
    content: str = "",
) -> dict[str, Any]:
    """Create a new FastBlocks template.

    Args:
        name: Template name (e.g., "user_card")
        template_type: Template engine (jinja2, htmy)
        variant: Template variant/theme (base, bulma, etc.)
        content: Template content (optional, uses default if empty)

    Returns:
        Dict with template creation status and path
    """
    try:
        # Determine template directory
        templates_root = Path.cwd() / "templates" / variant / "blocks"
        templates_root.mkdir(parents=True, exist_ok=True)

        # Determine file extension
        extension = ".html" if template_type == "jinja2" else ".py"
        template_path = templates_root / f"{name}{extension}"

        if template_path.exists():
            return {
                "success": False,
                "error": f"Template already exists: {template_path}",
                "path": str(template_path),
            }

        # Generate default content if not provided
        if not content:
            if template_type == "jinja2":
                content = f"""[# {name} template #]
<div class="{name}">
  [[ content ]]
</div>
"""
            else:  # htmy
                content = f'''"""HTMY component: {name}"""
from dataclasses import dataclass
from typing import Any


@dataclass
class {name.title().replace("_", "")}:
    """HTMY component for {name}."""

    content: str = ""

    def htmy(self, context: dict[str, Any]) -> str:
        return f"""
        <div class="{name}">
            {{self.content}}
        </div>
        """
'''

        # Write template file
        template_path.write_text(content)

        return {
            "success": True,
            "path": str(template_path),
            "type": template_type,
            "variant": variant,
        }

    except Exception as e:
        logger.error(f"Error creating template: {e}")
        return {"success": False, "error": str(e)}


async def validate_template(template_path: str) -> dict[str, Any]:
    """Validate a FastBlocks template for syntax errors.

    Args:
        template_path: Path to template file

    Returns:
        Dict with validation status and any errors found
    """
    try:
        path = Path(template_path)
        if not path.exists():
            return {"success": False, "error": f"Template not found: {template_path}"}

        content = path.read_text()

        # Get syntax support from ACB registry
        syntax_support = await depends.get("syntax_support")
        if syntax_support is None:
            return {
                "success": False,
                "error": "Syntax support not available",
            }

        # Check syntax
        errors = syntax_support.check_syntax(content, path)

        if not errors:
            return {"success": True, "errors": [], "path": template_path}

        return {
            "success": False,
            "errors": [
                {
                    "line": e.line,
                    "column": e.column,
                    "message": e.message,
                    "severity": e.severity,
                    "code": e.code,
                    "fix_suggestion": e.fix_suggestion,
                }
                for e in errors
            ],
            "path": template_path,
        }

    except Exception as e:
        logger.error(f"Error validating template: {e}")
        return {"success": False, "error": str(e)}


def _should_skip_variant_dir(variant_dir: Path, variant_filter: str | None) -> bool:
    """Check if variant directory should be skipped.

    Args:
        variant_dir: Variant directory path
        variant_filter: Optional variant filter

    Returns:
        True if should skip, False otherwise
    """
    if not variant_dir.is_dir():
        return True

    if variant_filter and variant_dir.name != variant_filter:
        return True

    return False


def _determine_template_type(suffix: str) -> str:
    """Determine template type from file suffix.

    Args:
        suffix: File suffix (e.g., '.html', '.py')

    Returns:
        Template type ('jinja2' or 'htmy')
    """
    return "jinja2" if suffix == ".html" else "htmy"


def _create_template_info(template_file: Path, variant_name: str) -> dict[str, str]:
    """Create template info dictionary.

    Args:
        template_file: Template file path
        variant_name: Variant directory name

    Returns:
        Template info dict
    """
    return {
        "name": template_file.stem,
        "path": str(template_file),
        "variant": variant_name,
        "type": _determine_template_type(template_file.suffix),
    }


def _collect_variant_templates(variant_dir: Path) -> list[dict[str, str]]:
    """Collect all template files from a variant directory.

    Args:
        variant_dir: Variant directory path

    Returns:
        List of template info dicts
    """
    templates: list[dict[str, str]] = []
    blocks_dir = variant_dir / "blocks"

    if not blocks_dir.exists():
        return templates

    for template_file in blocks_dir.rglob("*"):
        if template_file.is_file() and template_file.suffix in (".html", ".py"):
            templates.append(_create_template_info(template_file, variant_dir.name))

    return templates


async def list_templates(variant: str | None = None) -> dict[str, Any]:
    """List all available FastBlocks templates.

    Args:
        variant: Optional variant filter (base, bulma, etc.)

    Returns:
        Dict with list of discovered templates
    """
    try:
        templates_root = Path.cwd() / "templates"

        # Guard clause: no templates directory
        if not templates_root.exists():
            return {"success": True, "templates": [], "count": 0}

        templates: list[dict[str, str]] = []

        # Search for template files in each variant directory
        for variant_dir in templates_root.iterdir():
            if _should_skip_variant_dir(variant_dir, variant):
                continue

            templates.extend(_collect_variant_templates(variant_dir))

        return {
            "success": True,
            "templates": sorted(templates, key=operator.itemgetter("name")),
            "count": len(templates),
        }

    except Exception as e:
        logger.error(f"Error listing templates: {e}")
        return {"success": False, "error": str(e)}


async def render_template(
    template_name: str, context: dict[str, Any] | None = None, variant: str = "base"
) -> dict[str, Any]:
    """Render a template with given context for testing.

    Args:
        template_name: Template name to render
        context: Template context variables
        variant: Template variant (base, bulma, etc.)

    Returns:
        Dict with rendered output or error
    """
    try:
        # Get template adapter from ACB
        templates = await depends.get("templates")
        if templates is None:
            return {
                "success": False,
                "error": "Template adapter not available",
            }

        # Render template
        context = context or {}
        rendered = await templates.render(
            f"{variant}/blocks/{template_name}.html", context
        )

        return {
            "success": True,
            "output": rendered,
            "template": template_name,
            "variant": variant,
        }

    except Exception as e:
        logger.error(f"Error rendering template: {e}")
        return {"success": False, "error": str(e)}


# Component Management Tools


async def create_component(
    name: str,
    component_type: str = "dataclass",
    props: dict[str, str] | None = None,
    htmx_enabled: bool = False,
) -> dict[str, Any]:
    """Create a new HTMY component.

    Args:
        name: Component name
        component_type: Component type (basic, dataclass, htmx, composite)
        props: Component properties as {name: type}
        htmx_enabled: Enable HTMX features

    Returns:
        Dict with component creation status
    """
    try:
        htmy_adapter = await depends.get("htmy")
        if htmy_adapter is None:
            return {
                "success": False,
                "error": "HTMY adapter not available",
            }

        from fastblocks.adapters.templates._htmy_components import ComponentType

        # Map string type to ComponentType enum
        type_map = {
            "basic": ComponentType.BASIC,
            "dataclass": ComponentType.DATACLASS,
            "htmx": ComponentType.HTMX,
            "composite": ComponentType.COMPOSITE,
        }

        comp_type = type_map.get(component_type.lower(), ComponentType.DATACLASS)

        # Scaffold component
        kwargs: dict[str, Any] = {}
        if props:
            kwargs["props"] = props
        if htmx_enabled:
            kwargs["htmx_enabled"] = htmx_enabled

        created_path = await htmy_adapter.scaffold_component(
            name=name, component_type=comp_type, **kwargs
        )

        return {
            "success": True,
            "path": str(created_path),
            "name": name,
            "type": component_type,
        }

    except Exception as e:
        logger.error(f"Error creating component: {e}")
        return {"success": False, "error": str(e)}


async def list_components() -> dict[str, Any]:
    """List all discovered HTMY components.

    Returns:
        Dict with list of components and metadata
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
            "success": True,
            "components": [
                {
                    "name": name,
                    "path": str(metadata.path),
                    "type": metadata.type.value,
                    "status": metadata.status.value,
                    "docstring": metadata.docstring,
                    "error": metadata.error_message,
                }
                for name, metadata in components.items()
            ],
            "count": len(components),
        }

    except Exception as e:
        logger.error(f"Error listing components: {e}")
        return {"success": False, "error": str(e)}


async def validate_component(component_name: str) -> dict[str, Any]:
    """Validate an HTMY component.

    Args:
        component_name: Component name to validate

    Returns:
        Dict with validation status and metadata
    """
    try:
        htmy_adapter = await depends.get("htmy")
        if htmy_adapter is None:
            return {
                "success": False,
                "error": "HTMY adapter not available",
            }

        metadata = await htmy_adapter.validate_component(component_name)

        return {
            "success": metadata.status.value != "error",
            "component": component_name,
            "type": metadata.type.value,
            "status": metadata.status.value,
            "path": str(metadata.path),
            "docstring": metadata.docstring,
            "error": metadata.error_message,
            "dependencies": metadata.dependencies,
        }

    except Exception as e:
        logger.error(f"Error validating component: {e}")
        return {"success": False, "error": str(e)}


# Adapter Configuration Tools


async def configure_adapter(
    adapter_name: str, settings: dict[str, Any]
) -> dict[str, Any]:
    """Configure a FastBlocks adapter.

    Args:
        adapter_name: Adapter name (e.g., "templates", "auth")
        settings: Adapter configuration settings

    Returns:
        Dict with configuration status
    """
    try:
        # Get adapter from ACB registry
        adapter = await depends.get(adapter_name)
        if adapter is None:
            return {
                "success": False,
                "error": f"Adapter '{adapter_name}' not found",
            }

        # Update adapter settings
        for key, value in settings.items():
            if hasattr(adapter, key):
                setattr(adapter, key, value)

        return {
            "success": True,
            "adapter": adapter_name,
            "settings": settings,
        }

    except Exception as e:
        logger.error(f"Error configuring adapter: {e}")
        return {"success": False, "error": str(e)}


async def list_adapters(category: str | None = None) -> dict[str, Any]:
    """List all available FastBlocks adapters.

    Args:
        category: Optional category filter

    Returns:
        Dict with list of adapters and metadata
    """
    try:
        discovery = AdapterDiscoveryServer()
        adapters = await discovery.discover_adapters()

        # Filter by category if specified
        if category:
            adapters = {
                name: info
                for name, info in adapters.items()
                if info.category == category
            }

        return {
            "success": True,
            "adapters": [info.to_dict() for info in adapters.values()],
            "count": len(adapters),
            "categories": list({info.category for info in adapters.values()}),
        }

    except Exception as e:
        logger.error(f"Error listing adapters: {e}")
        return {"success": False, "error": str(e)}


async def check_adapter_health(adapter_name: str | None = None) -> dict[str, Any]:
    """Check health status of adapters.

    Args:
        adapter_name: Optional specific adapter to check

    Returns:
        Dict with health check results
    """
    try:
        from .registry import AdapterRegistry

        # Create registry and health system
        registry = AdapterRegistry()
        health_system = HealthCheckSystem(registry)
        results_dict = await health_system.check_all_adapters()

        # Convert to list of dicts
        results = [
            {"adapter": name} | result.to_dict()
            for name, result in results_dict.items()
        ]

        # Filter by adapter if specified
        if adapter_name:
            results = [r for r in results if r["adapter"] == adapter_name]

        return {
            "success": True,
            "checks": results,
            "count": len(results),
            "healthy": sum(1 for r in results if r["status"] == "healthy"),
            "unhealthy": sum(1 for r in results if r["status"] != "healthy"),
        }

    except Exception as e:
        logger.error(f"Error checking adapter health: {e}")
        return {"success": False, "error": str(e)}


# Tool registration function


async def register_fastblocks_tools(server: Any) -> None:
    """Register all FastBlocks MCP tools with the server.

    Args:
        server: MCP server instance from ACB
    """
    try:
        from acb.mcp import register_tools  # type: ignore[attr-defined]

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
        await register_tools(server, tools)  # type: ignore[misc]

        logger.info(f"Registered {len(tools)} FastBlocks MCP tools")

    except Exception as e:
        logger.error(f"Failed to register MCP tools: {e}")
        raise
