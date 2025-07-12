"""Template component gathering to consolidate loader, extension, processor, and filter collection."""

import typing as t
from contextlib import suppress
from importlib import import_module
from inspect import isclass

from acb.debug import debug
from anyio import Path as AsyncPath
from jinja2.ext import Extension

from .strategies import GatherStrategy, gather_with_strategy


class TemplateGatherResult:
    def __init__(
        self,
        *,
        loaders: list[t.Any] | None = None,
        extensions: list[t.Any] | None = None,
        context_processors: list[t.Callable[..., t.Any]] | None = None,
        filters: dict[str, t.Callable[..., t.Any]] | None = None,
        globals: dict[str, t.Any] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.loaders = loaders if loaders is not None else []
        self.extensions = extensions if extensions is not None else []
        self.context_processors = (
            context_processors if context_processors is not None else []
        )
        self.filters = filters if filters is not None else {}
        self.globals = globals if globals is not None else {}
        self.errors = errors if errors is not None else []

    @property
    def total_components(self) -> int:
        return (
            len(self.loaders)
            + len(self.extensions)
            + len(self.context_processors)
            + len(self.filters)
            + len(self.globals)
        )

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0


async def gather_templates(
    *,
    template_paths: list[AsyncPath] | None = None,
    loader_types: list[str] | None = None,
    extension_modules: list[str] | None = None,
    context_processor_paths: list[str] | None = None,
    filter_modules: list[str] | None = None,
    admin_mode: bool = False,
    strategy: GatherStrategy | None = None,
) -> TemplateGatherResult:
    config = _prepare_template_gather_config(
        template_paths,
        loader_types,
        extension_modules,
        context_processor_paths,
        filter_modules,
        admin_mode,
        strategy,
    )
    result = TemplateGatherResult()

    tasks = _build_template_gather_tasks(config)

    gather_result = await gather_with_strategy(
        tasks,
        config["strategy"],
        cache_key=f"templates:{admin_mode}:{':'.join(config['loader_types'])}",
    )

    _process_template_gather_results(gather_result, result)

    result.errors.extend(gather_result.errors)
    debug(f"Gathered {result.total_components} template components")

    return result


def _prepare_template_gather_config(
    template_paths: list[AsyncPath] | None,
    loader_types: list[str] | None,
    extension_modules: list[str] | None,
    context_processor_paths: list[str] | None,
    filter_modules: list[str] | None,
    admin_mode: bool,
    strategy: GatherStrategy | None,
) -> dict[str, t.Any]:
    if loader_types is None:
        loader_types = ["redis", "storage", "filesystem"]
        if admin_mode:
            loader_types.append("package")

    return {
        "template_paths": template_paths
        if template_paths is not None
        else [AsyncPath("templates")],
        "loader_types": loader_types,
        "extension_modules": extension_modules,
        "context_processor_paths": context_processor_paths,
        "filter_modules": filter_modules,
        "admin_mode": admin_mode,
        "strategy": strategy or GatherStrategy(),
    }


def _build_template_gather_tasks(
    config: dict[str, t.Any],
) -> list[t.Coroutine[t.Any, t.Any, t.Any]]:
    tasks = []

    tasks.append(
        _gather_loaders(
            config["template_paths"],
            config["loader_types"],
            config["admin_mode"],
        ),
    )

    if config["extension_modules"]:
        tasks.append(_gather_extensions(config["extension_modules"]))
    else:
        tasks.append(_gather_default_extensions())

    if config["context_processor_paths"]:
        tasks.append(_gather_context_processors(config["context_processor_paths"]))
    else:
        tasks.append(_gather_default_context_processors())

    if config["filter_modules"]:
        tasks.append(_gather_filters(config["filter_modules"]))
    else:
        tasks.append(_gather_default_filters())

    tasks.append(_gather_template_globals())

    return tasks


def _process_template_gather_results(
    gather_result: t.Any,
    result: TemplateGatherResult,
) -> None:
    component_mapping = [
        "loaders",
        "extensions",
        "context_processors",
        "filters",
        "globals",
    ]

    for i, success in enumerate(gather_result.success):
        if i < len(component_mapping):
            setattr(result, component_mapping[i], success)


async def _gather_loaders(
    template_paths: list[AsyncPath],
    loader_types: list[str],
    admin_mode: bool,
) -> list[t.Any]:
    try:
        jinja2_module = __import__(
            "fastblocks.adapters.templates.jinja2",
            fromlist=[
                "ChoiceLoader",
                "FileSystemLoader",
                "PackageLoader",
                "RedisLoader",
                "StorageLoader",
            ],
        )
        jinja2_module.ChoiceLoader
        FileSystemLoader = jinja2_module.FileSystemLoader
        PackageLoader = jinja2_module.PackageLoader
        RedisLoader = jinja2_module.RedisLoader
        StorageLoader = jinja2_module.StorageLoader
    except (ImportError, AttributeError) as e:
        debug(f"Error loading template loader classes: {e}")
        raise

    searchpaths: list[AsyncPath] = []
    for path in template_paths:
        searchpaths.extend([path, path / "blocks"])

    loaders = []

    if "redis" in loader_types:
        loaders.append(RedisLoader(searchpaths))

    if "storage" in loader_types:
        loaders.append(StorageLoader(searchpaths))

    if "filesystem" in loader_types:
        loaders.append(FileSystemLoader(searchpaths))

    if "package" in loader_types and admin_mode:
        try:
            from acb.adapters import get_adapter

            enabled_admin = get_adapter("admin")
            if enabled_admin:
                loaders.append(PackageLoader(enabled_admin.name, "templates", "admin"))
        except Exception as e:
            debug(f"Could not create package loader: {e}")

    debug(f"Created {len(loaders)} template loaders")
    return loaders


async def _gather_extensions(extension_modules: list[str]) -> list[t.Any]:
    extensions = []
    from jinja2.ext import debug as jinja_debug
    from jinja2.ext import i18n, loopcontrols

    extensions.extend([loopcontrols, i18n, jinja_debug])
    for module_path in extension_modules:
        try:
            module = import_module(module_path)
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isclass(attr)
                    and attr.__name__ != "Extension"
                    and issubclass(attr, Extension)
                ):
                    extensions.append(attr)
                    debug(f"Found extension {attr.__name__} in {module_path}")
        except Exception as e:
            debug(f"Error loading extensions from {module_path}: {e}")
    debug(f"Gathered {len(extensions)} Jinja2 extensions")
    return extensions


async def _gather_default_extensions() -> list[t.Any]:
    from jinja2.ext import debug as jinja_debug
    from jinja2.ext import i18n, loopcontrols

    extensions = [loopcontrols, i18n, jinja_debug]
    await _load_config_extensions(extensions)

    return extensions


async def _load_config_extensions(extensions: list[t.Any]) -> None:
    with suppress(Exception):
        from acb.depends import depends

        config = depends.get("config")
        if _has_template_extensions_config(config):
            _process_extension_paths(config.templates.extensions, extensions)


def _has_template_extensions_config(config: t.Any) -> bool:
    return hasattr(config, "templates") and hasattr(config.templates, "extensions")


def _process_extension_paths(ext_paths: list[str], extensions: list[t.Any]) -> None:
    for ext_path in ext_paths:
        try:
            module = import_module(ext_path)
            _extract_extension_classes_from_module(module, extensions)
        except Exception as e:
            debug(f"Error loading extension {ext_path}: {e}")


def _extract_extension_classes_from_module(
    module: t.Any,
    extensions: list[t.Any],
) -> None:
    for attr_name in dir(module):
        attr = getattr(module, attr_name)
        if _is_valid_extension_class(attr):
            extensions.append(attr)


def _is_valid_extension_class(attr: t.Any) -> bool:
    return (
        isclass(attr) and attr.__name__ != "Extension" and issubclass(attr, Extension)
    )


async def _gather_context_processors(
    processor_paths: list[str],
) -> list[t.Callable[..., t.Any]]:
    processors = []
    for processor_path in processor_paths:
        try:
            module_path, func_name = processor_path.rsplit(".", 1)
            module = import_module(module_path)
            processor = getattr(module, func_name)
            if callable(processor):
                processors.append(processor)
                debug(f"Found context processor {func_name} in {module_path}")
            else:
                debug(f"Context processor {func_name} is not callable")
        except Exception as e:
            debug(f"Error loading context processor {processor_path}: {e}")
    debug(f"Gathered {len(processors)} context processors")
    return processors


async def _gather_default_context_processors() -> list[t.Callable[..., t.Any]]:
    processors = []
    with suppress(Exception):
        from acb.depends import depends

        config = depends.get("config")
        if hasattr(config, "templates") and hasattr(
            config.templates,
            "context_processors",
        ):
            for processor_path in config.templates.context_processors:
                try:
                    module_path, func_name = processor_path.rsplit(".", 1)
                    module = import_module(module_path)
                    processor = getattr(module, func_name)
                    if callable(processor):
                        processors.append(processor)
                except Exception as e:
                    debug(f"Error loading context processor {processor_path}: {e}")

    return processors


async def _gather_filters(
    filter_modules: list[str],
) -> dict[str, t.Callable[..., t.Any]]:
    filters = {}
    for module_path in filter_modules:
        try:
            module = import_module(module_path)
            _extract_filters_from_module(module, module_path, filters)
        except Exception as e:
            debug(f"Error loading filters from {module_path}: {e}")
    debug(f"Gathered {len(filters)} template filters")
    return filters


def _extract_filters_from_module(
    module: t.Any,
    module_path: str,
    filters: dict[str, t.Callable[..., t.Any]],
) -> None:
    if hasattr(module, "Filters"):
        filters_class = module.Filters
        _extract_filters_from_class(filters_class, module_path, filters)

    _extract_filter_functions(module, module_path, filters)


def _extract_filters_from_class(
    filters_class: t.Any,
    module_path: str,
    filters: dict[str, t.Callable[..., t.Any]],
) -> None:
    for attr_name in dir(filters_class):
        if not attr_name.startswith("_"):
            attr = getattr(filters_class, attr_name)
            if callable(attr):
                filters[attr_name] = attr
                debug(f"Found filter {attr_name} in {module_path}")


def _extract_filter_functions(
    module: t.Any,
    module_path: str,
    filters: dict[str, t.Callable[..., t.Any]],
) -> None:
    for attr_name in dir(module):
        if attr_name.endswith("_filter") and not attr_name.startswith("_"):
            attr = getattr(module, attr_name)
            if callable(attr):
                filter_name = attr_name.removesuffix("_filter")
                filters[filter_name] = attr
                debug(f"Found filter function {filter_name} in {module_path}")


async def _gather_default_filters() -> dict[str, t.Callable[..., t.Any]]:
    filters = {}
    try:
        filters_module = __import__(
            "fastblocks.adapters.templates._filters",
            fromlist=["Filters"],
        )
        Filters = filters_module.Filters
        for attr_name in dir(Filters):
            if not attr_name.startswith("_") and attr_name != "register_filters":
                attr = getattr(Filters, attr_name)
                if callable(attr):
                    filters[attr_name] = attr
    except (ImportError, AttributeError) as e:
        debug(f"Error loading default filters: {e}")

    return filters


async def _gather_template_globals() -> dict[str, t.Any]:
    globals_dict = {}
    try:
        from acb.depends import depends

        config = depends.get("config")
        globals_dict["config"] = config
        try:
            models = depends.get("models")
            globals_dict["models"] = models
        except Exception:
            globals_dict["models"] = None
        if hasattr(config, "templates") and hasattr(config.templates, "globals"):
            globals_dict.update(config.templates.globals)
    except Exception as e:
        debug(f"Error gathering template globals: {e}")

    return globals_dict


async def create_choice_loader(
    loaders: list[t.Any],
    config: t.Any | None = None,
) -> t.Any:
    try:
        jinja2_module = __import__(
            "fastblocks.adapters.templates.jinja2",
            fromlist=["ChoiceLoader"],
        )
        ChoiceLoader = jinja2_module.ChoiceLoader
    except (ImportError, AttributeError) as e:
        debug(f"Error loading ChoiceLoader: {e}")
        raise

    ordered_loaders = []

    if config and not getattr(config, "deployed", False):
        filesystem_loaders = [
            loader for loader in loaders if "FileSystem" in str(type(loader))
        ]
        other_loaders = [
            loader for loader in loaders if "FileSystem" not in str(type(loader))
        ]
        ordered_loaders = filesystem_loaders + other_loaders
    else:
        cache_loaders = [
            loader
            for loader in loaders
            if any(x in str(type(loader)) for x in ("Redis", "Storage"))
        ]
        other_loaders = [
            loader
            for loader in loaders
            if not any(x in str(type(loader)) for x in ("Redis", "Storage"))
        ]
        ordered_loaders = cache_loaders + other_loaders

    debug(f"Created ChoiceLoader with {len(ordered_loaders)} loaders")
    return ChoiceLoader(ordered_loaders)


async def create_template_environment(
    gather_result: TemplateGatherResult,
    cache: t.Any | None = None,
) -> t.Any:
    from jinja2_async_environment.bccache import AsyncRedisBytecodeCache
    from starlette_async_jinja import AsyncJinja2Templates

    bytecode_cache = AsyncRedisBytecodeCache(prefix="bccache", client=cache)

    choice_loader = await create_choice_loader(gather_result.loaders)

    templates = AsyncJinja2Templates(
        directory=AsyncPath("templates"),
        context_processors=gather_result.context_processors,
        extensions=gather_result.extensions,
        bytecode_cache=bytecode_cache,
        enable_async=True,
    )

    if choice_loader:
        templates.env.loader = choice_loader

    for name, value in gather_result.globals.items():
        templates.env.globals[name] = value

    for name, filter_func in gather_result.filters.items():
        templates.env.filters[name] = filter_func

    templates.env.block_start_string = "[%"
    templates.env.block_end_string = "%]"
    templates.env.variable_start_string = "[["
    templates.env.variable_end_string = "]]"
    templates.env.comment_start_string = "[#"
    templates.env.comment_end_string = "#]"

    debug("Created Jinja2 environment with gathered components")
    return templates


def register_template_filters(
    templates: t.Any,
    filters: dict[str, t.Callable[..., t.Any]],
) -> None:
    for name, filter_func in filters.items():
        if hasattr(templates, "filter"):
            templates.filter(name)(filter_func)
        else:
            templates.env.filters[name] = filter_func

    debug(f"Registered {len(filters)} template filters")
