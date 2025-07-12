"""Application component gathering and initialization orchestration."""

import typing as t
from importlib import import_module

from acb.adapters import get_adapters
from acb.debug import debug

from .strategies import GatherStrategy, gather_with_strategy


class ApplicationGatherResult:
    def __init__(
        self,
        *,
        adapters: dict[str, t.Any] | None = None,
        acb_modules: dict[str, t.Any] | None = None,
        dependencies: dict[str, t.Any] | None = None,
        initializers: list[t.Callable[..., t.Any]] | None = None,
        config: t.Any | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.adapters = adapters if adapters is not None else {}
        self.acb_modules = acb_modules if acb_modules is not None else {}
        self.dependencies = dependencies if dependencies is not None else {}
        self.initializers = initializers if initializers is not None else []
        self.config = config
        self.errors = errors if errors is not None else []

    @property
    def total_components(self) -> int:
        return (
            len(self.adapters)
            + len(self.acb_modules)
            + len(self.dependencies)
            + len(self.initializers)
        )

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


async def gather_application(
    *,
    include_adapters: bool = True,
    include_acb_modules: bool = True,
    include_dependencies: bool = True,
    include_initializers: bool = True,
    adapter_patterns: list[str] | None = None,
    dependency_patterns: list[str] | None = None,
    strategy: GatherStrategy | None = None,
) -> ApplicationGatherResult:
    config = _prepare_application_gather_config(
        adapter_patterns,
        dependency_patterns,
        strategy,
    )
    result = ApplicationGatherResult()

    tasks = _build_application_gather_tasks(
        config,
        include_adapters,
        include_acb_modules,
        include_dependencies,
        include_initializers,
    )

    gather_result = await gather_with_strategy(
        tasks,
        config["strategy"],
        cache_key=f"application:{include_adapters}:{include_acb_modules}:{':'.join(config['dependency_patterns'])}",
    )

    _process_application_gather_results(
        gather_result,
        result,
        include_adapters,
        include_acb_modules,
        include_dependencies,
        include_initializers,
    )

    await _gather_application_config(result)

    result.errors.extend(gather_result.errors)
    debug(f"Gathered {result.total_components} application components")

    return result


def _prepare_application_gather_config(
    adapter_patterns: list[str] | None,
    dependency_patterns: list[str] | None,
    strategy: GatherStrategy | None,
) -> dict[str, t.Any]:
    return {
        "adapter_patterns": adapter_patterns
        or ["__init__.py", "models.py", "views.py"],
        "dependency_patterns": dependency_patterns
        or ["models", "config", "cache", "database"],
        "strategy": strategy or GatherStrategy(),
    }


def _build_application_gather_tasks(
    config: dict[str, t.Any],
    include_adapters: bool,
    include_acb_modules: bool,
    include_dependencies: bool,
    include_initializers: bool,
) -> list[t.Coroutine[t.Any, t.Any, t.Any]]:
    tasks = []

    if include_adapters:
        tasks.append(_gather_adapters_and_modules(config["adapter_patterns"]))
    if include_acb_modules:
        tasks.append(_gather_acb_modules())
    if include_dependencies:
        tasks.append(_gather_application_dependencies(config["dependency_patterns"]))
    if include_initializers:
        tasks.append(_gather_initializers())

    return tasks


def _process_application_gather_results(
    gather_result: t.Any,
    result: ApplicationGatherResult,
    include_adapters: bool,
    include_acb_modules: bool,
    include_dependencies: bool,
    include_initializers: bool,
) -> None:
    for i, success in enumerate(gather_result.success):
        task_index = 0

        if include_adapters and i == task_index:
            result.adapters = success.get("adapters", {})
            result.acb_modules.update(success.get("adapter_modules", {}))
            task_index += 1
            continue

        if include_acb_modules and i == task_index:
            result.acb_modules.update(success)
            task_index += 1
            continue

        if include_dependencies and i == task_index:
            result.dependencies = success
            task_index += 1
            continue

        if include_initializers and i == task_index:
            result.initializers = success


async def _gather_application_config(result: ApplicationGatherResult) -> None:
    try:
        result.config = await _gather_config()
    except Exception as e:
        result.errors.append(e)


async def _gather_adapters_and_modules(adapter_patterns: list[str]) -> dict[str, t.Any]:
    adapters_info: dict[str, t.Any] = {
        "adapters": {},
        "adapter_modules": {},
    }
    for adapter in get_adapters():
        adapter_name = adapter.name
        adapters_info["adapters"][adapter_name] = adapter
        for pattern in adapter_patterns:
            try:
                if pattern == "__init__.py":
                    module_path = f"acb.adapters.{adapter_name}"
                    module = import_module(module_path)
                    adapters_info["adapter_modules"][f"{adapter_name}_init"] = module
                    debug(f"Loaded adapter module: {module_path}")
                elif pattern.endswith(".py"):
                    module_name = pattern.removesuffix(".py")
                    module_path = f"acb.adapters.{adapter_name}.{module_name}"
                    try:
                        module = import_module(module_path)
                        adapters_info["adapter_modules"][
                            f"{adapter_name}_{module_name}"
                        ] = module
                        debug(f"Loaded adapter module: {module_path}")
                    except ModuleNotFoundError:
                        debug(f"Module {module_path} not found, skipping")
                        continue
            except Exception as e:
                debug(f"Error loading {adapter_name}/{pattern}: {e}")
    debug(
        f"Gathered {len(adapters_info['adapters'])} adapters and {len(adapters_info['adapter_modules'])} modules",
    )
    return adapters_info


async def _gather_acb_modules() -> dict[str, t.Any]:
    acb_modules = {}
    core_modules = [
        "acb.depends",
        "acb.config",
        "acb.debug",
        "acb.adapters",
    ]
    optional_modules = [
        "acb.storage",
        "acb.cache",
        "acb.queue",
        "acb.testing",
    ]
    for module_path in core_modules:
        try:
            module = import_module(module_path)
            module_name = module_path.split(".")[-1]
            acb_modules[module_name] = module
            debug(f"Loaded core ACB module: {module_path}")
        except Exception as e:
            debug(f"Error loading core ACB module {module_path}: {e}")
    for module_path in optional_modules:
        try:
            module = import_module(module_path)
            module_name = module_path.split(".")[-1]
            acb_modules[module_name] = module
            debug(f"Loaded optional ACB module: {module_path}")
        except ModuleNotFoundError:
            debug(f"Optional ACB module {module_path} not available")
        except Exception as e:
            debug(f"Error loading optional ACB module {module_path}: {e}")
    debug(f"Gathered {len(acb_modules)} ACB modules")
    return acb_modules


async def _gather_application_dependencies(
    dependency_patterns: list[str],
) -> dict[str, t.Any]:
    dependencies: dict[str, t.Any] = {}
    try:
        from acb.depends import depends

        for dep_name in dependency_patterns:
            try:
                dependency = depends.get(dep_name)
                if dependency is not None:
                    dependencies[dep_name] = dependency
                    debug(f"Gathered dependency: {dep_name}")
            except Exception as e:
                debug(f"Could not get dependency {dep_name}: {e}")
    except Exception as e:
        debug(f"Error accessing depends system: {e}")
    app_modules = [
        "models",
        "views",
        "utils",
        "services",
        "handlers",
    ]
    for module_name in app_modules:
        try:
            module = import_module(module_name)
            dependencies[f"app_{module_name}"] = module
            debug(f"Loaded application module: {module_name}")
        except ModuleNotFoundError:
            continue
        except Exception as e:
            debug(f"Error loading application module {module_name}: {e}")
    debug(f"Gathered {len(dependencies)} application dependencies")
    return dependencies


async def _gather_initializers() -> list[t.Callable[..., t.Any]]:
    initializers = []
    await _gather_standard_initializers(initializers)
    await _gather_adapter_initializers(initializers)
    debug(f"Gathered {len(initializers)} initialization functions")
    return initializers


async def _gather_standard_initializers(
    initializers: list[t.Callable[..., t.Any]],
) -> None:
    initializer_paths = [
        "initializers.init_app",
        "app.init_app",
        "main.init_app",
        "startup.init_app",
        "init.init_app",
    ]

    for init_path in initializer_paths:
        try:
            module_path, func_name = init_path.rsplit(".", 1)
            module = import_module(module_path)
            init_func = getattr(module, func_name)
            if callable(init_func):
                initializers.append(init_func)
                debug(f"Found initializer: {init_path}")
        except (ModuleNotFoundError, AttributeError):
            continue
        except Exception as e:
            debug(f"Error loading initializer {init_path}: {e}")


async def _gather_adapter_initializers(
    initializers: list[t.Callable[..., t.Any]],
) -> None:
    for adapter in get_adapters():
        try:
            adapter_init_path = f"acb.adapters.{adapter.name}.init"
            module = import_module(adapter_init_path)
            _collect_adapter_init_functions(module, adapter.name, initializers)
        except ModuleNotFoundError:
            continue
        except Exception as e:
            debug(f"Error loading adapter initializer for {adapter.name}: {e}")


def _collect_adapter_init_functions(
    module: t.Any,
    adapter_name: str,
    initializers: list[t.Callable[..., t.Any]],
) -> None:
    for func_name in ("init", "initialize", "setup", "configure"):
        if hasattr(module, func_name):
            init_func = getattr(module, func_name)
            if callable(init_func):
                initializers.append(init_func)
                debug(f"Found adapter initializer: {adapter_name}.{func_name}")


async def _gather_config() -> t.Any:
    try:
        from acb.depends import depends

        config = depends.get("config")
        if config:
            debug("Gathered application config from depends")
            return config
    except Exception as e:
        debug(f"Error getting config from depends: {e}")
    try:
        from acb.config import Config

        debug("Gathered application config directly")
        return Config()
    except Exception as e:
        debug(f"Error importing config directly: {e}")
        raise


async def initialize_application_components(
    gather_result: ApplicationGatherResult,
) -> dict[str, t.Any]:
    initialization_results: dict[str, t.Any] = {
        "adapters_initialized": [],
        "dependencies_set": [],
        "initializers_run": [],
        "errors": [],
    }

    for adapter_name in gather_result.adapters:
        try:
            initialization_results["adapters_initialized"].append(adapter_name)
            debug(f"Initialized adapter: {adapter_name}")

        except Exception as e:
            initialization_results["errors"].append(e)
            debug(f"Error initializing adapter {adapter_name}: {e}")

    try:
        from acb.depends import depends

        for dep_name, dependency in gather_result.dependencies.items():
            try:
                depends.set(dep_name, dependency)
                initialization_results["dependencies_set"].append(dep_name)
                debug(f"Set dependency: {dep_name}")

            except Exception as e:
                initialization_results["errors"].append(e)
                debug(f"Error setting dependency {dep_name}: {e}")

    except Exception as e:
        initialization_results["errors"].append(e)
        debug(f"Error accessing depends system: {e}")

    for i, initializer in enumerate(gather_result.initializers):
        try:
            import inspect

            sig = inspect.signature(initializer)

            if len(sig.parameters) > 0:
                result = initializer(gather_result.config)
            else:
                result = initializer()

            if inspect.iscoroutine(result):
                await result

            initialization_results["initializers_run"].append(f"initializer_{i}")
            debug(f"Ran initializer {i}")

        except Exception as e:
            initialization_results["errors"].append(e)
            debug(f"Error running initializer {i}: {e}")

    debug(
        f"Initialized {len(initialization_results['adapters_initialized'])} adapters, "
        f"{len(initialization_results['dependencies_set'])} dependencies, "
        f"{len(initialization_results['initializers_run'])} initializers",
    )

    return initialization_results


def get_application_info(gather_result: ApplicationGatherResult) -> dict[str, t.Any]:
    info: dict[str, t.Any] = {
        "total_components": gather_result.total_components,
        "adapters": {
            "count": len(gather_result.adapters),
            "names": list(gather_result.adapters.keys()),
        },
        "acb_modules": {
            "count": len(gather_result.acb_modules),
            "modules": list(gather_result.acb_modules.keys()),
        },
        "dependencies": {
            "count": len(gather_result.dependencies),
            "types": list(gather_result.dependencies.keys()),
        },
        "initializers": {
            "count": len(gather_result.initializers),
        },
        "config_available": gather_result.config is not None,
        "has_errors": gather_result.has_errors,
        "error_count": len(gather_result.errors),
    }
    if gather_result.config:
        info["config_info"] = {
            "type": type(gather_result.config).__name__,
            "deployed": getattr(gather_result.config, "deployed", False),
            "debug": getattr(gather_result.config, "debug", False),
        }

    return info


async def create_application_manager(
    gather_result: ApplicationGatherResult,
) -> t.Any:
    try:
        from fastblocks.applications import (
            ApplicationManager,  # type: ignore[attr-defined]
        )
    except ImportError:

        class SimpleApplicationManager:
            def __init__(self, gather_result: ApplicationGatherResult) -> None:
                self.adapters = gather_result.adapters
                self.dependencies = gather_result.dependencies
                self.config = gather_result.config
                self.initializers = gather_result.initializers

        return SimpleApplicationManager(gather_result)

    manager = ApplicationManager()

    manager._adapters = gather_result.adapters
    manager._dependencies = gather_result.dependencies
    manager._config = gather_result.config
    manager._initializers = gather_result.initializers

    debug(
        f"Created application manager with {gather_result.total_components} components",
    )

    return manager
