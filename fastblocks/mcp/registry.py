"""Central registry for FastBlocks adapter management."""

from contextlib import suppress
from typing import Any
from uuid import UUID

from acb.depends import depends

from .discovery import AdapterDiscoveryServer, AdapterInfo


class AdapterRegistry:
    """Central registry for managing FastBlocks adapters."""

    def __init__(self) -> None:
        """Initialize adapter registry."""
        self.discovery = AdapterDiscoveryServer()
        self._active_adapters: dict[str, Any] = {}
        self._adapter_dependencies: dict[str, set[str]] = {}
        self._adapter_config: dict[str, dict[str, Any]] = {}

    async def initialize(self) -> None:
        """Initialize the registry by discovering all adapters."""
        await self.discovery.discover_adapters()

    async def register_adapter(self, adapter_name: str, adapter_instance: Any) -> bool:
        """Register an adapter instance in the registry."""
        try:
            # Register with ACB system
            with suppress(Exception):
                depends.set(adapter_instance)

            # Track in our registry
            self._active_adapters[adapter_name] = adapter_instance

            return True
        except Exception:
            return False

    async def unregister_adapter(self, adapter_name: str) -> bool:
        """Unregister an adapter from the registry."""
        try:
            if adapter_name in self._active_adapters:
                del self._active_adapters[adapter_name]

            # TODO: Remove from ACB registry if possible
            return True
        except Exception:
            return False

    async def get_adapter(self, adapter_name: str) -> Any | None:
        """Get an adapter instance by name."""
        # Try active registry first
        if adapter_name in self._active_adapters:
            return self._active_adapters[adapter_name]

        # Try ACB registry
        with suppress(Exception):  # Try to instantiate from discovery
            adapter = await depends.get(adapter_name)
            if adapter:
                self._active_adapters[adapter_name] = adapter
                return adapter

        adapter = await self.discovery.instantiate_adapter(adapter_name)
        if adapter:
            await self.register_adapter(adapter_name, adapter)
            return adapter

        return None

    async def get_adapter_info(self, adapter_name: str) -> AdapterInfo | None:
        """Get adapter information by name."""
        return await self.discovery.get_adapter_by_name(adapter_name)

    async def list_available_adapters(self) -> dict[str, AdapterInfo]:
        """List all available adapters."""
        return await self.discovery.discover_adapters()

    async def list_active_adapters(self) -> dict[str, Any]:
        """List currently active (instantiated) adapters."""
        return self._active_adapters.copy()

    async def get_adapters_by_category(self, category: str) -> list[AdapterInfo]:
        """Get all adapters in a specific category."""
        return await self.discovery.get_adapters_by_category(category)

    async def get_categories(self) -> list[str]:
        """Get all available adapter categories."""
        return await self.discovery.get_all_categories()

    def _validate_module_id(self, adapter: Any, result: dict[str, Any]) -> None:
        """Validate adapter MODULE_ID attribute."""
        if not hasattr(adapter, "MODULE_ID"):
            result["warnings"].append("Missing MODULE_ID attribute")
        elif not isinstance(adapter.MODULE_ID, UUID):
            result["errors"].append("MODULE_ID is not a valid UUID")

    def _validate_module_status(self, adapter: Any, result: dict[str, Any]) -> None:
        """Validate adapter MODULE_STATUS attribute."""
        if not hasattr(adapter, "MODULE_STATUS"):
            result["warnings"].append("Missing MODULE_STATUS attribute")
        elif adapter.MODULE_STATUS not in (
            "stable",
            "beta",
            "alpha",
            "experimental",
        ):
            result["warnings"].append(f"Unknown MODULE_STATUS: {adapter.MODULE_STATUS}")

    def _validate_settings(self, adapter: Any, result: dict[str, Any]) -> None:
        """Validate adapter settings configuration."""
        if hasattr(adapter, "settings"):
            result["info"]["has_settings"] = True
            settings = adapter.settings
            if hasattr(settings, "__dict__"):
                result["info"]["settings_properties"] = list(settings.__dict__.keys())
        else:
            result["warnings"].append("No settings attribute found")

    async def validate_adapter(self, adapter_name: str) -> dict[str, Any]:
        """Validate an adapter's configuration and functionality."""
        result: dict[str, Any] = {
            "valid": False,
            "errors": [],
            "warnings": [],
            "info": {},
        }

        try:
            # Get adapter info
            info = await self.get_adapter_info(adapter_name)
            if not info:
                result["errors"].append(f"Adapter '{adapter_name}' not found")
                return result

            result["info"] = info.to_dict()

            # Try to get/instantiate adapter
            adapter = await self.get_adapter(adapter_name)
            if not adapter:
                result["errors"].append(
                    f"Failed to instantiate adapter '{adapter_name}'"
                )
                return result

            # Validate adapter attributes
            self._validate_module_id(adapter, result)
            self._validate_module_status(adapter, result)
            self._validate_settings(adapter, result)

            # If we got here without errors, adapter is valid
            if not result["errors"]:
                result["valid"] = True

        except Exception as e:
            result["errors"].append(f"Validation error: {e}")

        return result

    async def auto_register_available_adapters(self) -> dict[str, bool]:
        """Automatically register all available adapters."""
        results = {}
        available_adapters = await self.list_available_adapters()

        for adapter_name in available_adapters:
            try:
                adapter = await self.discovery.instantiate_adapter(adapter_name)
                if adapter:
                    success = await self.register_adapter(adapter_name, adapter)
                    results[adapter_name] = success
                else:
                    results[adapter_name] = False
            except Exception:
                results[adapter_name] = False

        return results

    async def get_adapter_statistics(self) -> dict[str, Any]:
        """Get comprehensive statistics about adapters."""
        available = await self.list_available_adapters()
        active = await self.list_active_adapters()
        categories = await self.get_categories()

        stats: dict[str, Any] = {
            "total_available": len(available),
            "total_active": len(active),
            "total_categories": len(categories),
            "categories": {},
            "status_breakdown": {},
            "active_adapters": list(active.keys()),
            "inactive_adapters": [name for name in available if name not in active],
        }

        # Category breakdown
        categories_dict: dict[str, dict[str, Any]] = {}
        for category in categories:
            category_adapters = await self.get_adapters_by_category(category)
            categories_dict[category] = {
                "total": len(category_adapters),
                "adapters": [adapter.name for adapter in category_adapters],
            }
        stats["categories"] = categories_dict

        # Status breakdown
        status_breakdown: dict[str, int] = {}
        for adapter_info in available.values():
            status = adapter_info.module_status
            if status not in status_breakdown:
                status_breakdown[status] = 0
            status_breakdown[status] += 1
        stats["status_breakdown"] = status_breakdown

        return stats

    def configure_adapter(self, adapter_name: str, config: dict[str, Any]) -> None:
        """Configure an adapter with custom settings."""
        self._adapter_config[adapter_name] = config

    def get_adapter_config(self, adapter_name: str) -> dict[str, Any]:
        """Get configuration for an adapter."""
        return self._adapter_config.get(adapter_name, {})

    def add_adapter_dependency(self, adapter_name: str, dependency: str) -> None:
        """Add a dependency relationship between adapters."""
        if adapter_name not in self._adapter_dependencies:
            self._adapter_dependencies[adapter_name] = set()
        self._adapter_dependencies[adapter_name].add(dependency)

    def get_adapter_dependencies(self, adapter_name: str) -> set[str]:
        """Get dependencies for an adapter."""
        return self._adapter_dependencies.get(adapter_name, set())

    async def resolve_dependencies(self, adapter_name: str) -> list[str]:
        """Resolve and load all dependencies for an adapter."""
        dependencies = self.get_adapter_dependencies(adapter_name)
        loaded = []

        for dep in dependencies:
            adapter = await self.get_adapter(dep)
            if adapter:
                loaded.append(dep)

        return loaded
