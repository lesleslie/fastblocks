"""Route gathering functionality to replace scattered route discovery."""

import typing as t
from contextlib import suppress
from importlib import import_module
from pathlib import Path

from acb.adapters import get_adapters, root_path
from acb.debug import debug
from anyio import Path as AsyncPath
from starlette.routing import Host, Mount, Route, Router, WebSocketRoute

from .strategies import GatherStrategy, gather_with_strategy

RouteType = Route | Router | Mount | Host | WebSocketRoute


class RouteGatherResult:
    def __init__(
        self,
        *,
        routes: list[RouteType] | None = None,
        adapter_routes: dict[str, list[RouteType]] | None = None,
        base_routes: list[RouteType] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.routes = routes if routes is not None else []
        self.adapter_routes = adapter_routes if adapter_routes is not None else {}
        self.base_routes = base_routes if base_routes is not None else []
        self.errors = errors if errors is not None else []

    @property
    def total_routes(self) -> int:
        return len(self.routes)

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def extend_routes(self, additional_routes: list[RouteType]) -> None:
        self.routes.extend(additional_routes)


async def gather_routes(
    *,
    sources: list[str] | None = None,
    patterns: list[str] | None = None,
    include_base: bool = True,
    include_adapters: bool = True,
    strategy: GatherStrategy | None = None,
) -> RouteGatherResult:
    if sources is None:
        sources = ["adapters", "base_routes"]

    if patterns is None:
        patterns = ["_routes.py", "routes.py"]

    if strategy is None:
        strategy = GatherStrategy()

    result = RouteGatherResult()

    tasks = []

    if "adapters" in sources and include_adapters:
        tasks.append(_gather_adapter_routes(patterns, strategy))

    if "base_routes" in sources and include_base:
        tasks.append(_gather_base_routes(patterns))

    if "custom" in sources:
        tasks.append(_gather_custom_routes(patterns, strategy))

    gather_result = await gather_with_strategy(
        tasks,
        strategy,
        cache_key=f"routes:{':'.join(sources)}:{':'.join(patterns)}",
    )

    for success in gather_result.success:
        if isinstance(success, dict):
            result.adapter_routes.update(success)
            for routes in success.values():
                result.routes.extend(routes)
        elif isinstance(success, list):
            result.base_routes.extend(success)
            result.routes.extend(success)

    result.errors.extend(gather_result.errors)

    debug(f"Gathered {result.total_routes} routes from {len(sources)} sources")

    return result


async def _gather_adapter_routes(
    patterns: list[str],
    strategy: GatherStrategy,
) -> dict[str, list[RouteType]]:
    adapter_routes = {}

    for adapter in get_adapters():
        await _process_adapter_routes(adapter, patterns, strategy, adapter_routes)

    return adapter_routes


async def _process_adapter_routes(
    adapter: t.Any,
    patterns: list[str],
    strategy: GatherStrategy,
    adapter_routes: dict[str, list[RouteType]],
) -> None:
    adapter_name = adapter.name
    adapter_path = adapter.path.parent
    routes = []

    for pattern in patterns:
        routes_path = adapter_path / pattern

        if await AsyncPath(routes_path).exists():
            try:
                found_routes = await _extract_routes_from_file(routes_path)
                if found_routes:
                    routes.extend(found_routes)
                    debug(
                        f"Found {len(found_routes)} routes in {adapter_name}/{pattern}",
                    )
            except Exception as e:
                debug(f"Error gathering routes from {adapter_name}/{pattern}: {e}")
                raise

    if routes:
        adapter_routes[adapter_name] = routes


async def _gather_base_routes(patterns: list[str]) -> list[RouteType]:
    base_routes = []
    for pattern in patterns:
        routes_path = root_path / pattern
        if await AsyncPath(routes_path).exists():
            try:
                routes = await _extract_routes_from_file(Path(routes_path))
                if routes:
                    base_routes.extend(routes)
                    debug(f"Found {len(routes)} base routes in {pattern}")
            except Exception as e:
                debug(f"Error gathering base routes from {pattern}: {e}")

    return base_routes


async def _gather_custom_routes(
    patterns: list[str],
    strategy: GatherStrategy,
) -> list[RouteType]:
    custom_routes = []

    custom_paths = [
        root_path / "app" / "routes.py",
        root_path / "custom" / "routes.py",
        root_path / "src" / "routes.py",
    ]

    for custom_path in custom_paths:
        if await AsyncPath(custom_path).exists():
            try:
                routes = await _extract_routes_from_file(Path(custom_path))
                if routes:
                    custom_routes.extend(routes)
                    debug(f"Found {len(routes)} custom routes in {custom_path}")

            except Exception as e:
                debug(f"Error gathering custom routes from {custom_path}: {e}")
                if strategy.error_strategy.value == "fail_fast":
                    raise

    return custom_routes


async def _extract_routes_from_file(file_path: Path) -> list[RouteType]:
    module_path = _get_module_path_from_file_path(file_path)
    debug(f"Extracting routes from {file_path} -> {module_path}")
    try:
        with suppress(ModuleNotFoundError, ImportError):
            module = import_module(module_path)
            return _extract_routes_from_module(module, module_path)
    except Exception as e:
        debug(f"Error extracting routes from {file_path}: {e}")
        raise

    return []


def _get_module_path_from_file_path(file_path: Path) -> str:
    depth = -2
    if "adapters" in file_path.parts:
        depth = -4
    return ".".join(file_path.parts[depth:]).removesuffix(".py")


def _extract_routes_from_module(module: t.Any, module_path: str) -> list[RouteType]:
    if not hasattr(module, "routes"):
        debug(f"No routes attribute found in {module_path}")
        return []
    module_routes = module.routes
    if not isinstance(module_routes, list):
        debug(f"Routes attribute in {module_path} is not a list: {type(module_routes)}")
        return []

    return _validate_route_objects(module_routes)


def _validate_route_objects(module_routes: list[t.Any]) -> list[RouteType]:
    valid_routes = []
    for route in module_routes:
        if isinstance(route, Route | Router | Mount | Host | WebSocketRoute):
            valid_routes.append(route)
        else:
            debug(f"Skipping invalid route object: {type(route)}")

    return valid_routes


async def gather_route_patterns(
    route_objects: list[RouteType],
) -> dict[str, t.Any]:
    patterns: dict[str, t.Any] = {
        "total_routes": len(route_objects),
        "route_types": {},
        "path_patterns": [],
        "methods": set(),
        "endpoints": set(),
    }

    for route in route_objects:
        route_type = type(route).__name__
        patterns["route_types"][route_type] = (
            patterns["route_types"].get(route_type, 0) + 1
        )

        path = getattr(route, "path", None)
        if path is not None:
            patterns["path_patterns"].append(path)

        methods = getattr(route, "methods", None)
        if methods is not None:
            patterns["methods"].update(methods)

        endpoint = getattr(route, "endpoint", None)
        if endpoint is not None:
            endpoint_name = getattr(endpoint, "__name__", str(endpoint))
            patterns["endpoints"].add(endpoint_name)

    patterns["methods"] = list(patterns["methods"])
    patterns["endpoints"] = list(patterns["endpoints"])

    return patterns


def create_default_routes() -> list[RouteType]:
    try:
        routes_module = __import__(
            "fastblocks.adapters.routes.default",
            fromlist=["Routes"],
        )
        Routes = routes_module.Routes
        routes_instance = Routes()
        return [
            Route("/favicon.ico", endpoint=routes_instance.favicon, methods=["GET"]),
            Route("/robots.txt", endpoint=routes_instance.robots, methods=["GET"]),
        ]
    except (ImportError, AttributeError) as e:
        debug(f"Error loading default routes: {e}")
        return []


async def validate_routes(routes: list[RouteType]) -> dict[str, t.Any]:
    validation: dict[str, t.Any] = {
        "valid_routes": [],
        "invalid_routes": [],
        "warnings": [],
        "total_checked": len(routes),
    }
    path_patterns = set()
    for route in routes:
        _validate_single_route(route, validation, path_patterns)

    return validation


def _validate_single_route(
    route: RouteType,
    validation: dict[str, t.Any],
    path_patterns: set[str],
) -> None:
    try:
        path = getattr(route, "path", None)
        if path is None:
            validation["invalid_routes"].append(
                {"route": str(route), "error": "Missing path attribute"},
            )
            return

        _check_route_path_duplicates(route, validation, path_patterns)
        _check_route_endpoint(route, validation)
        validation["valid_routes"].append(route)

    except Exception as e:
        validation["invalid_routes"].append({"route": str(route), "error": str(e)})


def _check_route_path_duplicates(
    route: RouteType,
    validation: dict[str, t.Any],
    path_patterns: set[str],
) -> None:
    path = getattr(route, "path", None)
    if path is not None:
        if path in path_patterns:
            validation["warnings"].append(f"Duplicate path: {path}")
        path_patterns.add(path)


def _check_route_endpoint(route: RouteType, validation: dict[str, t.Any]) -> None:
    endpoint = getattr(route, "endpoint", None)
    path = getattr(route, "path", "unknown")
    if hasattr(route, "endpoint") and endpoint is None:
        validation["warnings"].append(f"Route {path} has no endpoint")
