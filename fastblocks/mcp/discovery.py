"""MCP server for FastBlocks adapter discovery and introspection."""

import importlib
import inspect
from contextlib import suppress
from pathlib import Path
from typing import Any
from uuid import UUID

from acb.config import AdapterBase
from acb.depends import depends


class AdapterInfo:
    """Information about a discovered adapter."""

    def __init__(
        self,
        name: str,
        module_path: str,
        class_name: str,
        module_id: UUID,
        module_status: str,
        category: str,
        description: str = "",
        protocols: list[str] | None = None,
        settings_class: str = "",
    ):
        self.name = name
        self.module_path = module_path
        self.class_name = class_name
        self.module_id = module_id
        self.module_status = module_status
        self.category = category
        self.description = description
        self.protocols = protocols or []
        self.settings_class = settings_class

    def to_dict(self) -> dict[str, Any]:
        """Convert adapter info to dictionary."""
        return {
            "name": self.name,
            "module_path": self.module_path,
            "class_name": self.class_name,
            "module_id": str(self.module_id),
            "module_status": self.module_status,
            "category": self.category,
            "description": self.description,
            "protocols": self.protocols,
            "settings_class": self.settings_class,
        }


class AdapterDiscoveryServer:
    """MCP server for discovering and introspecting FastBlocks adapters."""

    def __init__(self, adapters_root: Path | None = None):
        """Initialize discovery server."""
        self.adapters_root = adapters_root or Path(__file__).parent.parent / "adapters"
        self._discovered_adapters: dict[str, AdapterInfo] = {}
        self._category_map: dict[str, list[str]] = {}

    async def discover_adapters(self) -> dict[str, AdapterInfo]:
        """Discover all available adapters in the FastBlocks system."""
        if self._discovered_adapters:
            return self._discovered_adapters

        self._discovered_adapters = {}
        self._category_map = {}

        # Discover adapters from filesystem
        await self._discover_from_filesystem()

        # Discover adapters from ACB registry
        await self._discover_from_acb_registry()

        return self._discovered_adapters

    async def _discover_from_filesystem(self) -> None:
        """Discover adapters by scanning the filesystem."""
        if not self.adapters_root.exists():
            return

        for category_dir in self.adapters_root.iterdir():
            if not category_dir.is_dir() or category_dir.name.startswith("_"):
                continue

            category = category_dir.name
            self._category_map[category] = []

            for adapter_file in category_dir.iterdir():
                if (
                    adapter_file.is_file()
                    and adapter_file.suffix == ".py"
                    and not adapter_file.name.startswith("_")
                ):
                    await self._inspect_adapter_file(adapter_file, category)

    async def _discover_from_acb_registry(self) -> None:
        """Discover adapters from ACB dependency registry."""
        with suppress(Exception):
            # Try to get adapters from ACB registry
            # This may not be available in all ACB versions
            from acb.depends import depends

            # Get all registered instances that might be adapters
            registry = getattr(depends, "_registry", {})

            for _key, adapter in registry.items():
                if hasattr(adapter, "MODULE_ID") and hasattr(adapter, "MODULE_STATUS"):
                    adapter_name = adapter.__class__.__name__.lower().replace(
                        "adapter", ""
                    )

                    if adapter_name not in self._discovered_adapters:
                        # Try to determine category from module path
                        module_path = adapter.__class__.__module__
                        category = self._extract_category_from_module(module_path)

                        info = AdapterInfo(
                            name=adapter_name,
                            module_path=module_path,
                            class_name=adapter.__class__.__name__,
                            module_id=adapter.MODULE_ID,
                            module_status=adapter.MODULE_STATUS,
                            category=category,
                            description=self._extract_description(adapter.__class__),
                            protocols=self._extract_protocols(adapter.__class__),
                            settings_class=self._extract_settings_class(
                                adapter.__class__
                            ),
                        )

                        self._discovered_adapters[adapter_name] = info

                        if category not in self._category_map:
                            self._category_map[category] = []
                        self._category_map[category].append(adapter_name)

    async def _inspect_adapter_file(self, adapter_file: Path, category: str) -> None:
        """Inspect a single adapter file for adapter classes."""
        with suppress(Exception):
            module_name = f"fastblocks.adapters.{category}.{adapter_file.stem}"

            with suppress(Exception):
                module = importlib.import_module(module_name)

                for name, obj in inspect.getmembers(module, inspect.isclass):
                    if (
                        obj.__module__ == module_name
                        and self._is_adapter_class(obj)
                        and not name.endswith(("Base", "Protocol"))
                    ):
                        adapter_name = name.lower().replace("adapter", "")

                        info = AdapterInfo(
                            name=adapter_name,
                            module_path=module_name,
                            class_name=name,
                            module_id=getattr(
                                obj,
                                "MODULE_ID",
                                UUID("00000000-0000-0000-0000-000000000000"),
                            ),
                            module_status=getattr(obj, "MODULE_STATUS", "unknown"),
                            category=category,
                            description=self._extract_description(obj),
                            protocols=self._extract_protocols(obj),
                            settings_class=self._extract_settings_class(obj),
                        )

                        self._discovered_adapters[adapter_name] = info
                        self._category_map[category].append(adapter_name)

    def _is_adapter_class(self, cls: type) -> bool:
        """Check if a class is an adapter class."""
        return (
            issubclass(cls, AdapterBase)
            or hasattr(cls, "MODULE_ID")
            or any("adapter" in base.__name__.lower() for base in cls.__bases__)
        )

    def _extract_category_from_module(self, module_path: str) -> str:
        """Extract category from module path."""
        parts = module_path.split(".")
        for i, part in enumerate(parts):
            if part == "adapters" and i + 1 < len(parts):
                return parts[i + 1]
        return "unknown"

    def _extract_description(self, cls: type) -> str:
        """Extract description from class docstring."""
        doc = cls.__doc__
        if doc:
            return doc.split("\n")[0].strip('."""')
        return ""

    def _extract_protocols(self, cls: type) -> list[str]:
        """Extract implemented protocols from class."""
        return [
            base.__name__
            for base in cls.__bases__
            if hasattr(base, "__name__") and "protocol" in base.__name__.lower()
        ]

    def _extract_settings_class(self, cls: type) -> str:
        """Extract settings class name from adapter."""
        # Look for settings attribute or Settings class in module
        if hasattr(cls, "settings"):
            settings_obj = getattr(cls, "settings", None)
            if hasattr(settings_obj, "__class__"):
                return settings_obj.__class__.__name__

        # Look for Settings class in same module
        with suppress(Exception):
            module = importlib.import_module(cls.__module__)
            for name, obj in inspect.getmembers(module, inspect.isclass):
                if name.endswith("Settings") and obj.__module__ == cls.__module__:
                    return name

        return ""

    async def get_adapter_by_name(self, name: str) -> AdapterInfo | None:
        """Get adapter information by name."""
        adapters = await self.discover_adapters()
        return adapters.get(name)

    async def get_adapters_by_category(self, category: str) -> list[AdapterInfo]:
        """Get all adapters in a specific category."""
        adapters = await self.discover_adapters()
        return [adapters[name] for name in self._category_map.get(category, [])]

    async def get_all_categories(self) -> list[str]:
        """Get all available adapter categories."""
        await self.discover_adapters()
        return list(self._category_map.keys())

    async def get_adapter_instance(self, name: str) -> Any | None:
        """Get an actual adapter instance from ACB registry."""
        try:
            return depends.get(name)
        except Exception:
            return None

    async def instantiate_adapter(self, name: str) -> Any | None:
        """Instantiate an adapter by name."""
        adapter_info = await self.get_adapter_by_name(name)
        if not adapter_info:
            return None

        try:
            module = importlib.import_module(adapter_info.module_path)
            adapter_class = getattr(module, adapter_info.class_name)
            return adapter_class()
        except Exception:
            return None
