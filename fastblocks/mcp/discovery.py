"""MCP server for FastBlocks adapter discovery and introspection."""

from __future__ import annotations

import importlib
import inspect
from contextlib import suppress
from pathlib import Path
from typing import TYPE_CHECKING, Any
from uuid import UUID

from fastblocks.core.resolver import FastblocksRegistry, get_resolver

if TYPE_CHECKING:
    from mcp.server.fastmcp import FastMCP

# Lazy resolver dependency. ``depends`` is left None at import time so
# the discovery module can be imported even when ``FastblocksRegistry``
# is patched in a test. The first call to ``resolve_depends()`` lazy-
# initializes it; existing tests that ``monkeypatch.setattr`` ``depends``
# directly on this module continue to win over the lazy cache.
depends: FastblocksRegistry | None = None
_depends: FastblocksRegistry | None = None


def resolve_depends() -> FastblocksRegistry:
    """Return the active ``FastblocksRegistry`` for adapter resolution.

    Honors ``monkeypatch.setattr(discovery, "depends", X)`` by checking
    the module-level ``depends`` first; falls back to lazy
    initialization via ``FastblocksRegistry(get_resolver())``.
    """
    module_depends = globals().get("depends")
    if module_depends is not None:
        return module_depends
    global _depends
    if _depends is None:
        _depends = FastblocksRegistry(get_resolver())
    return _depends


# Custom AdapterBase for Oneiric compatibility
class AdapterBase:
    """Custom AdapterBase for Oneiric compatibility."""


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
        """Discover adapters from the Oneiric dependency resolver.

        Iterates registered Candidates (not a phantom ``_registry`` of
        instances, which Oneiric never exposed) and resolves each into
        an adapter-shaped object. The outer try/except is intentionally
        narrow: a single bad candidate no longer masks the whole pass.
        """
        try:
            candidates = resolve_depends().list_active("fastblocks")
        except (AttributeError, KeyError, RuntimeError, TypeError) as exc:
            # Resolver transport failure: the registry probe itself is best-effort.
            # We log + return rather than silently swallow.
            self._log_registry_probe_failure(exc)
            return

        for candidate in candidates:
            # Per-candidate scope: a single bad candidate is logged then
            # skipped, not silently absorbed for the whole pass.
            try:
                instance = self._resolve_candidate_instance(candidate)
            except (AttributeError, KeyError, RuntimeError, TypeError, ImportError, ValueError) as exc:
                self._log_candidate_resolution_failure(candidate.key, exc)
                continue

            if not hasattr(instance, "MODULE_ID") or not hasattr(
                instance, "MODULE_STATUS"
            ):
                continue

            adapter_cls = instance.__class__
            adapter_name = (
                adapter_cls.__name__.lower().replace("adapter", "").strip("_") or candidate.key
            )

            if adapter_name in self._discovered_adapters:
                continue

            module_path = adapter_cls.__module__
            category = self._extract_category_from_module(module_path)

            info = AdapterInfo(
                name=adapter_name,
                module_path=module_path,
                class_name=adapter_cls.__name__,
                module_id=instance.MODULE_ID,
                module_status=instance.MODULE_STATUS,
                category=category,
                description=self._extract_description(adapter_cls),
                protocols=self._extract_protocols(adapter_cls),
                settings_class=self._extract_settings_class(adapter_cls),
            )

            self._discovered_adapters[adapter_name] = info
            self._category_map.setdefault(category, []).append(adapter_name)

    @staticmethod
    def _log_registry_probe_failure(exc: BaseException) -> None:
        """Log a transport-level failure probing the registry.

        Visible to operators (not swallowed) but never raised — discovery
        is opportunistic metadata, not a hard dependency for app boot.
        """
        import logging

        logging.getLogger(__name__).warning(
            "fastblocks.mcp.discovery: registry probe failed: %s", exc,
        )

    @staticmethod
    def _log_candidate_resolution_failure(key: str, exc: BaseException) -> None:
        """Log a per-candidate resolution failure.

        Replaces the old `with suppress(Exception)` blanket. One bad
        candidate must not silently kill discovery of the rest.
        """
        import logging

        logging.getLogger(__name__).warning(
            "fastblocks.mcp.discovery: skipping candidate %r: %s", key, exc,
        )

    @staticmethod
    def _resolve_candidate_instance(candidate: Any) -> Any:
        """Return a live instance for a registered Candidate.

        Oneiric's ``Candidate.factory`` is a union of ``Callable[..., Any]``
        and ``str`` (the latter denotes an import path the resolver
        should resolve). For the callable branch we invoke the factory
        directly. For the string branch we import the dotted target
        and grab the attribute the resolver expects.
        """
        factory = candidate.factory
        if isinstance(factory, str):
            module_name, _, attr = factory.partition(":")
            if not module_name or not attr:
                raise ValueError(
                    f"candidate {candidate.key!r}: string factory {factory!r}"
                    " must be 'module.path:attribute'",
                )
            module = importlib.import_module(module_name)
            return getattr(module, attr)
        return factory()

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
            first_line = doc.split("\n")[0]
            return first_line.strip().strip('"\'.')
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
            return resolve_depends().resolve("fastblocks", name)
        except (KeyError, AttributeError, RuntimeError):
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
        except (ImportError, AttributeError, TypeError):
            return None


# ---------------------------------------------------------------------------
# Phase 4 v2.1 — FastBlocks-specific discovery_fn for ``apply_tool_profile``.
#
# Override of mcp_common's ``_default_discovery`` to add the
# ``capability`` field consumers need. Opt-in: consumers pass this as
# ``discovery_fn=fastblocks_discovery`` to their own apply_tool_profile
# call. If consumers don't pass it, mcp_common's default shape is used
# (no capability tag).
#
# Schema: ``{name, capability, description, inputSchema}``. There is
# no ``is_available`` field — tools that fail a capability gate are
# NOT in ``server.list_tools()`` (gate failures skip registration
# entirely, per mcp_common contract).
# ---------------------------------------------------------------------------
async def fastblocks_discovery(
    server: FastMCP, filter_query: str | None
) -> list[dict]:
    """Emit {name, capability, description, inputSchema}.

    Walks the server's registered tools and looks up each name in
    ``get_tool_capability()``.
    """
    from fastblocks.mcp.capabilities import get_tool_capability

    tools = await server.list_tools()
    result: list[dict] = []
    for t in tools:
        capability = get_tool_capability(t.name)
        result.append(
            {
                "name": t.name,
                "capability": capability,
                "description": t.description or "",
                "inputSchema": t.inputSchema,
            }
        )
    if filter_query:
        q = filter_query.lower()
        result = [
            t
            for t in result
            if q in str(t["name"]).lower()
            or q in str(t["capability"]).lower()
            or q in str(t["description"]).lower()
        ]
    return result


__all__ = ["fastblocks_discovery"]
