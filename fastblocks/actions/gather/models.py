"""Model gathering functionality to discover and collect SQLModel and Pydantic models."""

import inspect
import typing as t
from contextlib import suppress
from importlib import import_module
from pathlib import Path

from acb.adapters import get_adapters, root_path
from acb.debug import debug
from anyio import Path as AsyncPath

from .strategies import GatherStrategy, gather_with_strategy


class ModelGatherResult:
    def __init__(
        self,
        *,
        sql_models: dict[str, type] | None = None,
        nosql_models: dict[str, type] | None = None,
        adapter_models: dict[str, dict[str, type]] | None = None,
        admin_models: list[type] | None = None,
        model_metadata: dict[str, dict[str, t.Any]] | None = None,
        errors: list[Exception] | None = None,
    ) -> None:
        self.sql_models = sql_models if sql_models is not None else {}
        self.nosql_models = nosql_models if nosql_models is not None else {}
        self.adapter_models = adapter_models if adapter_models is not None else {}
        self.admin_models = admin_models if admin_models is not None else []
        self.model_metadata = model_metadata if model_metadata is not None else {}
        self.errors = errors if errors is not None else []

    @property
    def total_models(self) -> int:
        adapter_count = sum(len(models) for models in self.adapter_models.values())
        return len(self.sql_models) + len(self.nosql_models) + adapter_count

    @property
    def has_errors(self) -> bool:
        return len(self.errors) > 0

    def get_all_models(self) -> dict[str, type]:
        all_models = {}
        all_models.update(self.sql_models)
        all_models.update(self.nosql_models)
        for adapter_models in self.adapter_models.values():
            all_models.update(adapter_models)
        return all_models


async def gather_models(
    *,
    sources: list[str] | None = None,
    patterns: list[str] | None = None,
    include_base: bool = True,
    include_adapters: bool = True,
    include_admin: bool = True,
    base_classes: list[type] | None = None,
    strategy: GatherStrategy | None = None,
) -> ModelGatherResult:
    config = _prepare_model_gather_config(sources, patterns, base_classes, strategy)
    result = ModelGatherResult()

    tasks = _build_model_gather_tasks(config, include_base, include_adapters)
    gather_result = await gather_with_strategy(
        tasks,
        config["strategy"],
        cache_key=f"models:{':'.join(config['sources'])}:{':'.join(config['patterns'])}",
    )

    _process_model_gather_results(gather_result, config["sources"], result)

    if include_admin:
        admin_models = await _gather_admin_models(result.get_all_models())
        result.admin_models = admin_models

    result.errors.extend(gather_result.errors)
    debug(
        f"Gathered {result.total_models} models from {len(config['sources'])} sources",
    )

    return result


def _prepare_model_gather_config(
    sources: list[str] | None,
    patterns: list[str] | None,
    base_classes: list[type] | None,
    strategy: GatherStrategy | None,
) -> dict[str, t.Any]:
    return {
        "sources": sources if sources is not None else ["base", "adapters"],
        "patterns": patterns
        if patterns is not None
        else ["models.py", "_models.py", "_models_*.py"],
        "base_classes": base_classes
        if base_classes is not None
        else _get_default_model_base_classes(),
        "strategy": strategy if strategy is not None else GatherStrategy(),
    }


def _get_default_model_base_classes() -> list[type]:
    base_classes = []
    with suppress(ImportError):
        from sqlmodel import SQLModel  # type: ignore[import-untyped]

        base_classes.append(SQLModel)
    with suppress(ImportError):
        from pydantic import BaseModel  # type: ignore[import-untyped]

        base_classes.append(BaseModel)

    return base_classes


def _build_model_gather_tasks(
    config: dict[str, t.Any],
    include_base: bool,
    include_adapters: bool,
) -> list[t.Coroutine[t.Any, t.Any, t.Any]]:
    tasks = []
    sources = config["sources"]
    patterns = config["patterns"]
    base_classes = config["base_classes"]

    if "base" in sources and include_base:
        tasks.append(_gather_base_models(patterns, base_classes))

    if "adapters" in sources and include_adapters:
        tasks.append(_gather_adapter_models(patterns, base_classes))

    if "custom" in sources:
        tasks.append(_gather_custom_models(patterns, base_classes))

    return tasks


def _process_model_gather_results(
    gather_result: t.Any,
    sources: list[str],
    result: ModelGatherResult,
) -> None:
    for i, success in enumerate(gather_result.success):
        source_type = _get_model_source_type_by_index(i, sources)
        _process_single_model_source_result(success, source_type, result)


def _get_model_source_type_by_index(index: int, sources: list[str]) -> str:
    source_mapping = [("base", "base"), ("adapters", "adapters"), ("custom", "custom")]
    for i, (source_name, source_type) in enumerate(source_mapping):
        if i == index and source_name in sources:
            return source_type

    return "unknown"


def _process_single_model_source_result(
    success: dict[str, t.Any],
    source_type: str,
    result: ModelGatherResult,
) -> None:
    if source_type in ("base", "custom"):
        result.sql_models.update(success.get("sql", {}))
        result.nosql_models.update(success.get("nosql", {}))
        result.model_metadata.update(success.get("metadata", {}))
    elif source_type == "adapters":
        _process_adapter_models(success, result)


def _process_adapter_models(
    success: dict[str, t.Any],
    result: ModelGatherResult,
) -> None:
    result.adapter_models.update(success.get("adapter_models", {}))

    for models in success.get("adapter_models", {}).values():
        for model_name, model_class in models.items():
            if _is_sql_model(model_class):
                result.sql_models[model_name] = model_class
            else:
                result.nosql_models[model_name] = model_class

    result.model_metadata.update(success.get("metadata", {}))


async def _gather_base_models(
    patterns: list[str],
    base_classes: list[type],
) -> dict[str, t.Any]:
    base_models = {
        "sql": {},
        "nosql": {},
        "metadata": {},
    }

    models_file_path = Path(root_path) / "models.py"
    await _process_base_models_file(models_file_path, base_classes, base_models)

    await _process_base_models_directory(
        Path(root_path) / "models",
        base_classes,
        base_models,
    )

    return base_models


async def _process_base_models_file(
    models_file: Path,
    base_classes: list[type],
    base_models: dict[str, t.Any],
) -> None:
    if not await AsyncPath(models_file).exists():
        return

    try:
        models = await _extract_models_from_file(models_file, base_classes)
        _add_models_to_base_collection(models, str(models_file), base_models)
        debug(f"Found {len(models)} base models in models.py")
    except Exception as e:
        debug(f"Error gathering base models from models.py: {e}")


async def _process_base_models_directory(
    models_dir: Path,
    base_classes: list[type],
    base_models: dict[str, t.Any],
) -> None:
    if not (
        await AsyncPath(models_dir).exists() and await AsyncPath(models_dir).is_dir()
    ):
        return

    async for file_path in AsyncPath(models_dir).rglob("*.py"):
        if file_path.name.startswith("_"):
            continue

        try:
            models = await _extract_models_from_file(Path(file_path), base_classes)
            _add_models_to_base_collection(models, str(file_path), base_models)

            if models:
                debug(
                    f"Found {len(models)} models in {file_path.relative_to(root_path)}",
                )
        except Exception as e:
            debug(f"Error gathering models from {file_path}: {e}")


def _add_models_to_base_collection(
    models: dict[str, type],
    source_path: str,
    base_models: dict[str, t.Any],
) -> None:
    for model_name, model_class in models.items():
        if _is_sql_model(model_class):
            base_models["sql"][model_name] = model_class
        else:
            base_models["nosql"][model_name] = model_class

        base_models["metadata"][model_name] = {
            "source": source_path,
            "type": "sql" if _is_sql_model(model_class) else "nosql",
            "location": "base",
        }


async def _gather_adapter_models(
    patterns: list[str],
    base_classes: list[type],
) -> dict[str, t.Any]:
    adapter_models = {
        "adapter_models": {},
        "metadata": {},
    }

    for adapter in get_adapters():
        found_models = await _gather_single_adapter_models(
            adapter,
            patterns,
            base_classes,
            adapter_models,
        )

        if found_models:
            adapter_models["adapter_models"][adapter.name] = found_models

    return adapter_models


async def _gather_single_adapter_models(
    adapter: t.Any,
    patterns: list[str],
    base_classes: list[type],
    adapter_models: dict[str, t.Any],
) -> dict[str, type]:
    adapter_name = adapter.name
    adapter_path = adapter.path.parent
    found_models = {}

    for pattern in patterns:
        if "*" in pattern:
            found_models.update(
                await _gather_models_with_glob_pattern(
                    adapter_path,
                    pattern,
                    base_classes,
                    adapter_name,
                    adapter_models,
                ),
            )
        else:
            found_models.update(
                await _gather_models_with_exact_pattern(
                    adapter_path,
                    pattern,
                    base_classes,
                    adapter_name,
                    adapter_models,
                ),
            )

    return found_models


async def _gather_models_with_glob_pattern(
    adapter_path: t.Any,
    pattern: str,
    base_classes: list[type],
    adapter_name: str,
    adapter_models: dict[str, t.Any],
) -> dict[str, type]:
    found_models = {}

    async for file_path in AsyncPath(adapter_path).glob(pattern):
        if await file_path.is_file():
            try:
                models = await _extract_models_from_file(Path(file_path), base_classes)
                found_models.update(models)
                _store_adapter_model_metadata(
                    models,
                    adapter_name,
                    str(file_path),
                    adapter_models,
                )

                if models:
                    debug(
                        f"Found {len(models)} models in {adapter_name}/{file_path.name}",
                    )

            except Exception as e:
                debug(
                    f"Error gathering models from {adapter_name}/{file_path.name}: {e}",
                )

    return found_models


async def _gather_models_with_exact_pattern(
    adapter_path: t.Any,
    pattern: str,
    base_classes: list[type],
    adapter_name: str,
    adapter_models: dict[str, t.Any],
) -> dict[str, type]:
    found_models = {}
    file_path = adapter_path / pattern

    if await AsyncPath(file_path).exists():
        try:
            models = await _extract_models_from_file(Path(file_path), base_classes)
            found_models.update(models)
            _store_adapter_model_metadata(
                models,
                adapter_name,
                str(file_path),
                adapter_models,
            )

            if models:
                debug(f"Found {len(models)} models in {adapter_name}/{pattern}")

        except Exception as e:
            debug(f"Error gathering models from {adapter_name}/{pattern}: {e}")

    return found_models


def _store_adapter_model_metadata(
    models: dict[str, type],
    adapter_name: str,
    source_path: str,
    adapter_models: dict[str, t.Any],
) -> None:
    for model_name, model_class in models.items():
        adapter_models["metadata"][f"{adapter_name}.{model_name}"] = {
            "source": source_path,
            "type": "sql" if _is_sql_model(model_class) else "nosql",
            "location": "adapter",
            "adapter": adapter_name,
        }


async def _gather_custom_models(
    patterns: list[str],
    base_classes: list[type],
) -> dict[str, t.Any]:
    custom_models = {
        "sql": {},
        "nosql": {},
        "metadata": {},
    }

    custom_paths = [
        Path(root_path) / "app" / "models.py",
        Path(root_path) / "src" / "models.py",
        Path(root_path) / "custom" / "models.py",
    ]

    for custom_path in custom_paths:
        if await AsyncPath(custom_path).exists():
            await _process_custom_models_file(custom_path, base_classes, custom_models)

    return custom_models


async def _process_custom_models_file(
    custom_path: Path,
    base_classes: list[type],
    custom_models: dict[str, t.Any],
) -> None:
    try:
        models = await _extract_models_from_file(custom_path, base_classes)
        _add_custom_models_to_collection(models, str(custom_path), custom_models)

        if models:
            debug(f"Found {len(models)} custom models in {custom_path}")

    except Exception as e:
        debug(f"Error gathering custom models from {custom_path}: {e}")


def _add_custom_models_to_collection(
    models: dict[str, type],
    source_path: str,
    custom_models: dict[str, t.Any],
) -> None:
    for model_name, model_class in models.items():
        if _is_sql_model(model_class):
            custom_models["sql"][model_name] = model_class
        else:
            custom_models["nosql"][model_name] = model_class

        custom_models["metadata"][model_name] = {
            "source": source_path,
            "type": "sql" if _is_sql_model(model_class) else "nosql",
            "location": "custom",
        }


async def _extract_models_from_file(
    file_path: Path,
    base_classes: list[type],
) -> dict[str, type]:
    module_path = _get_module_path_from_file(file_path)
    debug(f"Extracting models from {file_path} -> {module_path}")

    try:
        with suppress(ModuleNotFoundError, ImportError):
            module = import_module(module_path)
            return _extract_models_from_module(module, base_classes)
    except Exception as e:
        debug(f"Error extracting models from {file_path}: {e}")
        raise

    return {}


def _get_module_path_from_file(file_path: Path) -> str:
    try:
        relative_path = file_path.relative_to(root_path)
        return str(relative_path).replace("/", ".").removesuffix(".py")
    except ValueError:
        return file_path.stem


def _extract_models_from_module(
    module: t.Any,
    base_classes: list[type],
) -> dict[str, type]:
    models = {}

    for attr_name in dir(module):
        if attr_name.startswith("_"):
            continue

        attr = getattr(module, attr_name)

        if _is_valid_model_class(attr, module, base_classes):
            models[attr_name] = attr

    return models


def _is_valid_model_class(attr: t.Any, module: t.Any, base_classes: list[type]) -> bool:
    if not (inspect.isclass(attr) and attr.__module__ == module.__name__):
        return False
    for base_class in base_classes:
        if issubclass(attr, base_class) and attr != base_class:
            return True

    return hasattr(attr, "__table__")


async def _gather_admin_models(
    all_models: dict[str, type],
) -> list[type]:
    admin_models = [
        model_class
        for model_class in all_models.values()
        if (
            hasattr(model_class, "__admin__")
            or hasattr(model_class, "can_create")
            or hasattr(model_class, "can_edit")
            or hasattr(model_class, "__table__")
        )
    ]

    debug(f"Found {len(admin_models)} admin-enabled models")

    return admin_models


def _is_sql_model(model_class: type) -> bool:
    if hasattr(model_class, "__table__"):
        return True
    if hasattr(model_class, "__tablename__"):
        return True
    return bool(model_class.__module__ and "sql" in model_class.__module__.lower())


async def create_models_namespace(
    gather_result: ModelGatherResult,
) -> t.Any:
    class SQLNamespace:
        pass

    class NoSQLNamespace:
        pass

    class ModelsNamespace:
        def __init__(self) -> None:
            self.sql = SQLNamespace()
            self.nosql = NoSQLNamespace()
            self._all_models = {}

        def get_admin_models(self) -> list[type]:
            return gather_result.admin_models

        def __getattr__(self, name: str) -> t.Any:
            if name in self._all_models:
                return self._all_models[name]
            msg = f"Model '{name}' not found"
            raise AttributeError(msg)

    models = ModelsNamespace()

    for model_name, model_class in gather_result.sql_models.items():
        setattr(models.sql, model_name, model_class)
        models._all_models[model_name] = model_class

    for model_name, model_class in gather_result.nosql_models.items():
        setattr(models.nosql, model_name, model_class)
        models._all_models[model_name] = model_class

    debug(f"Created models namespace with {len(models._all_models)} models")

    return models


async def validate_models(
    models: dict[str, type],
) -> dict[str, t.Any]:
    validation: dict[str, t.Any] = {
        "valid_models": [],
        "invalid_models": [],
        "warnings": [],
        "total_checked": len(models),
    }

    for model_name, model_class in models.items():
        try:
            _validate_single_model(model_name, model_class, validation)
        except Exception as e:
            validation["invalid_models"].append(
                {
                    "model": model_name,
                    "error": str(e),
                },
            )

    return validation


def _validate_single_model(
    model_name: str,
    model_class: type,
    validation: dict[str, t.Any],
) -> None:
    issues = []

    _check_model_definition(model_class, issues)

    _check_duplicate_model_name(model_name, validation)

    is_valid = _check_model_inheritance(model_class, issues)

    _categorize_model_validation_result(model_name, is_valid, issues, validation)


def _check_model_definition(model_class: type, issues: list[str]) -> None:
    if (
        not hasattr(model_class, "__table__")
        and not hasattr(
            model_class,
            "__tablename__",
        )
        and not hasattr(model_class, "__collection__")
    ):
        issues.append("Missing table/collection definition")


def _check_duplicate_model_name(model_name: str, validation: dict[str, t.Any]) -> None:
    if model_name in validation["valid_models"]:
        validation["warnings"].append(f"Duplicate model name: {model_name}")


def _check_model_inheritance(model_class: type, issues: list[str]) -> bool:
    if not any(hasattr(model_class, attr) for attr in ("__bases__", "__mro__")):
        issues.append("Invalid model inheritance")
        return False
    return True


def _categorize_model_validation_result(
    model_name: str,
    is_valid: bool,
    issues: list[str],
    validation: dict[str, t.Any],
) -> None:
    if is_valid and not issues:
        validation["valid_models"].append(model_name)
    else:
        validation["invalid_models"].append(
            {
                "model": model_name,
                "issues": issues,
            },
        )


def get_model_info(
    model_class: type,
    metadata: dict[str, t.Any] | None = None,
) -> dict[str, t.Any]:
    info: dict[str, t.Any] = {
        "name": model_class.__name__,
        "module": model_class.__module__,
        "type": "sql" if _is_sql_model(model_class) else "nosql",
        "attributes": [],
        "relationships": [],
    }

    if metadata:
        info.update(metadata)

    for attr_name in dir(model_class):
        if not attr_name.startswith("_"):
            attr = getattr(model_class, attr_name)
            if hasattr(attr, "__class__") and "Column" in attr.__class__.__name__:
                info["attributes"].append(attr_name)
            elif (
                hasattr(attr, "__class__") and "Relationship" in attr.__class__.__name__
            ):
                info["relationships"].append(attr_name)

    if hasattr(model_class, "__table__"):
        info["table_name"] = model_class.__table__.name
    elif hasattr(model_class, "__tablename__"):
        info["table_name"] = model_class.__tablename__
    elif hasattr(model_class, "__collection__"):
        info["collection_name"] = model_class.__collection__

    return info
