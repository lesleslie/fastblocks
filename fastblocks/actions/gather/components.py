"""FastBlocks Component Gathering Action.

Provides unified component discovery and management for HTMY components,
integrating with the gather action system to provide comprehensive component
orchestration across the FastBlocks ecosystem.

Features:
- Unified component discovery across all searchpaths
- Component metadata collection and analysis
- Performance-optimized gathering with parallel processing
- Integration with existing gather strategies
- HTMX-aware component categorization
- Advanced filtering and sorting capabilities

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

import asyncio
from contextlib import suppress
from dataclasses import dataclass, field
from datetime import datetime
from typing import Any

from acb.debug import debug
from acb.depends import depends
from anyio import Path as AsyncPath

from .strategies import GatherResult, GatherStrategy


@dataclass
class ComponentGatherResult(GatherResult):
    """Result from component gathering operation."""

    components: dict[str, Any] = field(default_factory=dict)
    component_count: int = 0
    validation_errors: list[str] = field(default_factory=list)
    htmx_components: list[str] = field(default_factory=list)
    dataclass_components: list[str] = field(default_factory=list)
    composite_components: list[str] = field(default_factory=list)
    searchpaths: list[AsyncPath] = field(default_factory=list)
    execution_time: float = 0.0
    items_processed: int = 0
    cache_hits: int = 0
    parallel_tasks: int = 0
    error_message: str = ""

    def __post_init__(self) -> None:
        # Initialize parent GatherResult
        success_items = list(self.components.values()) if self.components else []
        GatherResult.__init__(self, success=success_items, errors=[], cache_key=None)
        # Set component count
        self.component_count = len(self.components)


class ComponentGatherStrategy(GatherStrategy):
    """Strategy for gathering HTMY components."""

    def __init__(
        self,
        include_metadata: bool = True,
        validate_components: bool = True,
        filter_types: list[str] | None = None,
        max_parallel: int = 10,
        timeout: int = 300,
    ) -> None:
        super().__init__(
            max_concurrent=max_parallel,  # Map max_parallel to max_concurrent
            timeout=float(timeout),
            retry_attempts=2,
        )
        self.include_metadata = include_metadata
        self.validate_components = validate_components
        self.filter_types = filter_types or []
        # Store max_parallel for compatibility
        self.max_parallel = max_parallel

    async def gather_single(self, item: Any) -> Any:
        """Gather a single component."""
        if isinstance(item, dict) and "name" in item and "metadata" in item:
            return item
        return None

    async def gather_batch(self, items: list[Any]) -> list[Any]:
        """Gather a batch of components in parallel."""
        if not items:
            return []

        tasks = [self.gather_single(item) for item in items]
        results = await asyncio.gather(*tasks, return_exceptions=True)

        gathered = []
        for result in results:
            if isinstance(result, Exception):
                debug(f"Component gather error: {result}")
                continue
            if result is not None:
                gathered.append(result)

        return gathered


def _get_htmy_adapter(
    start_time: datetime,
) -> tuple[Any | None, ComponentGatherResult | None]:
    """Get HTMY adapter or return error result."""
    try:
        htmy_adapter = depends.get("htmy")
        return htmy_adapter, None
    except Exception as e:
        debug(f"Could not get HTMY adapter: {e}")
        result = ComponentGatherResult(
            error_message=f"HTMY adapter not available: {e}",
            execution_time=(datetime.now() - start_time).total_seconds(),
        )
        result.errors = [e]
        return None, result


async def _discover_components_metadata(htmy_adapter: Any) -> dict[str, Any]:
    """Discover components using adapter's discovery methods."""
    if hasattr(htmy_adapter, "discover_components"):
        metadata: dict[str, Any] = await htmy_adapter.discover_components()
        return metadata

    if hasattr(htmy_adapter, "htmy_registry") and htmy_adapter.htmy_registry:
        from fastblocks.adapters.templates._htmy_components import (
            ComponentMetadata,
            ComponentStatus,
            ComponentType,
        )

        discovered = await htmy_adapter.htmy_registry.discover_components()
        return {
            name: ComponentMetadata(
                name=name,
                path=path,
                type=ComponentType.BASIC,
                status=ComponentStatus.DISCOVERED,
            )
            for name, path in discovered.items()
        }

    return {}


def _categorize_and_validate(
    components_metadata: dict[str, Any], filter_types: list[str]
) -> tuple[list[str], list[str], list[str], list[str]]:
    """Categorize components and collect validation errors."""
    htmx_components = []
    dataclass_components = []
    composite_components = []
    validation_errors = []

    for name, metadata in components_metadata.items():
        if filter_types and metadata.type.value not in filter_types:
            continue

        if metadata.type.value == "htmx":
            htmx_components.append(name)
        elif metadata.type.value == "dataclass":
            dataclass_components.append(name)
        elif metadata.type.value == "composite":
            composite_components.append(name)

        if metadata.status.value == "error" and metadata.error_message:
            validation_errors.append(f"{name}: {metadata.error_message}")

    return (
        htmx_components,
        dataclass_components,
        composite_components,
        validation_errors,
    )


async def gather_components(
    htmy_adapter: Any | None = None,
    include_metadata: bool = True,
    validate_components: bool = True,
    filter_types: list[str] | None = None,
    searchpaths: list[AsyncPath] | None = None,
    strategy: ComponentGatherStrategy | None = None,
) -> ComponentGatherResult:
    """Gather all HTMY components with comprehensive metadata.

    Args:
        htmy_adapter: HTMY adapter instance (auto-detected if None)
        include_metadata: Include component metadata in results
        validate_components: Validate component structure
        filter_types: Filter components by type (htmx, dataclass, etc.)
        searchpaths: Custom searchpaths (uses adapter defaults if None)
        strategy: Custom gathering strategy

    Returns:
        ComponentGatherResult with discovered components and metadata
    """
    start_time = datetime.now()

    if strategy is None:
        strategy = ComponentGatherStrategy(
            include_metadata=include_metadata,
            validate_components=validate_components,
            filter_types=filter_types or [],
        )

    if htmy_adapter is None:
        htmy_adapter, error_result = _get_htmy_adapter(start_time)
        if error_result:
            return error_result

    if htmy_adapter is None:
        result = ComponentGatherResult(
            error_message="HTMY adapter not found",
            execution_time=(datetime.now() - start_time).total_seconds(),
        )
        result.errors = [Exception("HTMY adapter not found")]
        return result

    try:
        if hasattr(htmy_adapter, "_init_htmy_registry"):
            await htmy_adapter._init_htmy_registry()

        if searchpaths is None and hasattr(htmy_adapter, "component_searchpaths"):
            searchpaths = htmy_adapter.component_searchpaths
        elif searchpaths is None:
            searchpaths = []

        components_metadata = await _discover_components_metadata(htmy_adapter)

        htmx, dataclass, composite, validation_errors = _categorize_and_validate(
            components_metadata, strategy.filter_types
        )

        component_items = [
            {
                "name": name,
                "metadata": metadata,
                "type": metadata.type.value,
                "status": metadata.status.value,
                "path": str(metadata.path),
                "htmx_attributes": metadata.htmx_attributes,
                "dependencies": metadata.dependencies,
                "docstring": metadata.docstring,
                "last_modified": metadata.last_modified.isoformat()
                if metadata.last_modified
                else None,
                "error_message": metadata.error_message,
            }
            for name, metadata in components_metadata.items()
        ]

        gathered_components = await strategy.gather_batch(component_items)

        final_components = {
            item["name"]: item
            for item in gathered_components
            if item and "name" in item
        }

        execution_time = (datetime.now() - start_time).total_seconds()
        debug(f"Gathered {len(final_components)} components in {execution_time:.2f}s")

        result = ComponentGatherResult(
            components=final_components,
            component_count=len(final_components),
            validation_errors=validation_errors,
            htmx_components=htmx,
            dataclass_components=dataclass,
            composite_components=composite,
            searchpaths=searchpaths or [],
            execution_time=execution_time,
            items_processed=len(component_items),
            cache_hits=0,
            parallel_tasks=min(strategy.max_parallel, len(component_items)),
        )
        # Set success list with component values
        result.success = list(final_components.values()) if final_components else []
        return result

    except Exception as e:
        execution_time = (datetime.now() - start_time).total_seconds()
        debug(f"Component gathering failed: {e}")

        result = ComponentGatherResult(
            error_message=str(e),
            execution_time=execution_time,
            searchpaths=searchpaths or [],
        )
        result.errors = [e]
        return result


async def gather_component_dependencies(
    component_name: str,
    htmy_adapter: Any | None = None,
    recursive: bool = True,
    max_depth: int = 5,
) -> dict[str, Any]:
    """Gather component dependencies recursively.

    Args:
        component_name: Name of component to analyze
        htmy_adapter: HTMY adapter instance
        recursive: Whether to gather dependencies recursively
        max_depth: Maximum recursion depth

    Returns:
        Dictionary with component dependency tree
    """
    if htmy_adapter is None:
        htmy_adapter = depends.get("htmy")

    if htmy_adapter is None:
        return {"error": "HTMY adapter not available"}

    try:
        # Get component metadata
        if not hasattr(htmy_adapter, "validate_component"):
            return {"error": "Component validation not available"}

        metadata = await htmy_adapter.validate_component(component_name)

        dependencies = {
            "name": component_name,
            "type": metadata.type.value,
            "direct_dependencies": metadata.dependencies,
            "children": {},
        }

        if recursive and max_depth > 0:
            for dep in metadata.dependencies:
                with suppress(Exception):
                    child_deps = await gather_component_dependencies(
                        dep, htmy_adapter, recursive, max_depth - 1
                    )
                    dependencies["children"][dep] = child_deps

        return dependencies

    except Exception as e:
        return {"error": str(e)}


async def analyze_component_usage(
    htmy_adapter: Any | None = None,
) -> dict[str, Any]:
    """Analyze component usage patterns across the application.

    Args:
        htmy_adapter: HTMY adapter instance

    Returns:
        Dictionary with usage analysis
    """
    if htmy_adapter is None:
        htmy_adapter = depends.get("htmy")

    if htmy_adapter is None:
        return {"error": "HTMY adapter not available"}

    try:
        components_result = await gather_components(htmy_adapter)

        if not components_result.is_success:
            return {"error": components_result.error_message}

        analysis: dict[str, Any] = {
            "total_components": components_result.component_count,
            "by_type": {
                "htmx": len(components_result.htmx_components),
                "dataclass": len(components_result.dataclass_components),
                "composite": len(components_result.composite_components),
            },
            "validation_errors": len(components_result.validation_errors),
            "searchpaths": [str(p) for p in components_result.searchpaths],
            "components": {},
        }

        # Analyze each component
        for name, component_data in components_result.components.items():
            analysis["components"][name] = {
                "type": component_data.get("type"),
                "status": component_data.get("status"),
                "has_htmx": bool(component_data.get("htmx_attributes")),
                "dependency_count": len(component_data.get("dependencies", [])),
                "has_documentation": bool(component_data.get("docstring")),
                "last_modified": component_data.get("last_modified"),
            }

        return analysis

    except Exception as e:
        return {"error": str(e)}
