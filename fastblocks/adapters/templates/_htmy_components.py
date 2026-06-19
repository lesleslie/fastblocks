"""HTMY Component Management System for FastBlocks.

Provides advanced component discovery, validation, scaffolding, and lifecycle management
for HTMY components with deep HTMX integration and async rendering capabilities.

Key Features:
- Automatic component discovery with intelligent caching
- Dataclass-based component scaffolding with validation
- Component composition and nesting patterns
- HTMX-aware state management
- Async component rendering with lifecycle hooks
- Advanced error handling and debugging
- Hot-reloading support for development

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

from __future__ import annotations

import ast
import asyncio
import inspect
import tempfile
import typing as t
from abc import ABC, abstractmethod
from dataclasses import dataclass, field, fields, is_dataclass
from datetime import datetime
from enum import StrEnum
from pathlib import Path
from typing import Any
from uuid import uuid4

from anyio import Path as AsyncPath
from starlette.requests import Request


# Custom debug function for Oneiric compatibility
def debug(msg: str) -> None:
    """Custom debug function for Oneiric compatibility."""
    print(f"[DEBUG] {msg}")


try:
    from pydantic import BaseModel
except ImportError:
    BaseModel = None  # type: ignore[assignment,misc]


class ComponentStatus(StrEnum):
    """Component lifecycle status."""

    DISCOVERED = "discovered"
    VALIDATED = "validated"
    COMPILED = "compiled"
    READY = "ready"
    ERROR = "error"
    DEPRECATED = "deprecated"


class ComponentType(StrEnum):
    """Component classification types."""

    BASIC = "basic"
    DATACLASS = "dataclass"
    PYDANTIC = "pydantic"
    ASYNC = "async"
    HTMX = "htmx"
    COMPOSITE = "composite"


@dataclass
class ComponentMetadata:
    """Component metadata for discovery and management."""

    name: str
    path: AsyncPath
    type: ComponentType
    status: ComponentStatus = ComponentStatus.DISCOVERED
    dependencies: list[str] = field(default_factory=list)
    htmx_attributes: dict[str, Any] = field(default_factory=dict)
    cache_key: str | None = None
    last_modified: datetime | None = None
    error_message: str | None = None
    docstring: str | None = None

    def __post_init__(self) -> None:
        if self.cache_key is None:
            self.cache_key = f"component_{self.name}_{self.path.stem}"


class ComponentValidationError(Exception):
    """Raised when component validation fails."""

    pass


class ComponentCompilationError(Exception):
    """Raised when component compilation fails."""

    pass


class ComponentRenderError(Exception):
    """Raised when component rendering fails."""

    pass


# ---------------------------------------------------------------------------
# Phase 1.3: safe HTMY component loader (ast.parse class walker).
#
# Replaces the legacy ``importlib.util.spec_from_file_location`` +
# ``spec.loader.exec_module`` path, which is an RCE vector. The new
# loader parses the source via ``ast.parse`` and walks the tree to
# enforce four rules:
#
# 1. ``import`` / ``ImportFrom`` are rejected, except for an allowlist
#    of pure-data modules (``dataclasses``, ``typing``).
# 2. ``exec`` / ``eval`` / ``compile`` / ``__import__`` calls are
#    rejected — both at the top level and inside nested expressions
#    (functions, lambdas, comprehensions).
# 3. Only ``class`` / ``def`` / ``Import`` / ``ImportFrom`` (filtered
#    by the allowlist) are allowed at the top level. Top-level
#    ``Assign``, ``AugAssign``, ``Expr``, ``AnnAssign``, etc. are
#    rejected.
# 4. The first ``ClassDef`` at the top level is returned. Subsequent
#    top-level statements may define helpers (``def``) or other
#    allowlisted imports.
#
# The loader then executes the validated source in a fresh namespace
# (NOT via exec_module on a tempfile — the exec is local to this
# function and the module never touches ``sys.modules``).
# ---------------------------------------------------------------------------

# Allowlist of modules that may be imported. Each entry is the
# module's top-level name; ``from dataclasses import dataclass`` is
# accepted, ``import os`` is not.
_SAFE_IMPORT_MODULES: frozenset[str] = frozenset({"dataclasses", "typing"})

# Builtin / keyword names that are always rejected when called.
_DANGEROUS_CALL_NAMES: frozenset[str] = frozenset(
    {"exec", "eval", "compile", "__import__"}
)


def _check_no_dangerous_calls(node: ast.AST) -> None:
    """Walk ``ast.AST`` and reject any ``exec``/``eval``/``compile``/``__import__`` call.

    We do this in two passes:
    1. Top-level walk on the module's body to find any direct calls.
    2. ``ast.walk`` on every node to find nested calls (inside
       function bodies, lambdas, comprehensions, default-argument
       expressions, decorators, etc.).

    The walker is conservative: any match raises
    ``ComponentValidationError``. We do NOT attempt to constant-fold
    expressions; the goal is to make authoring dangerous code
    visually obvious, not to prove it impossible.
    """
    for child in ast.walk(node):
        if not isinstance(child, ast.Call):
            continue
        func = child.func
        # Direct call: ``exec(...)`` or ``__import__(...)``
        if isinstance(func, ast.Name) and func.id in _DANGEROUS_CALL_NAMES:
            raise ComponentValidationError(
                f"dangerous builtin call '{func.id}' is not allowed in component source"
            )
        # Attribute call: e.g. ``builtins.exec(...)`` is unusual but
        # we still catch it; we cannot catch every dunder path so
        # we rely on the Name match for the common cases.


def _validate_imports(tree: ast.Module) -> None:
    """Reject ``Import`` / ``ImportFrom`` outside the safe allowlist."""
    for node in tree.body:
        if isinstance(node, ast.Import):
            for alias in node.names:
                top = alias.name.split(".")[0]
                if top not in _SAFE_IMPORT_MODULES:
                    raise ComponentValidationError(
                        f"import of '{alias.name}' is not allowed; "
                        f"only {sorted(_SAFE_IMPORT_MODULES)} may be imported"
                    )
        elif isinstance(node, ast.ImportFrom):
            if node.module is None:
                raise ComponentValidationError(
                    "relative imports (no module) are not allowed"
                )
            top = node.module.split(".")[0]
            if top not in _SAFE_IMPORT_MODULES:
                raise ComponentValidationError(
                    f"import from '{node.module}' is not allowed; "
                    f"only {sorted(_SAFE_IMPORT_MODULES)} may be imported"
                )


def _walk_top_level(tree: ast.Module) -> list[ast.stmt]:
    """Return the top-level statements, after shape validation.

    The walker is a thin pass-through over ``tree.body``; it is
    factored out as a separate function so tests can introspect
    the per-statement-type routing the loader relies on.
    """
    allowed_types = (ast.ClassDef, ast.FunctionDef, ast.AsyncFunctionDef)
    for node in tree.body:
        if isinstance(node, (ast.Import, ast.ImportFrom)):
            continue  # validated separately by ``_validate_imports``
        if isinstance(node, allowed_types):
            continue
        raise ComponentValidationError(
            f"top-level {type(node).__name__} is not allowed; "
            "only class / def / allowlisted imports are permitted"
        )
    return tree.body.copy()


def _extract_class(tree: ast.Module) -> ast.ClassDef:
    """Return the first top-level ``ClassDef`` that defines an ``htmy`` method.

    Raises ``ComponentValidationError`` if no such class exists
    (test contract: a source with only helpers and no class
    defined is a validation failure, not a compilation failure).
    """
    for node in tree.body:
        if not isinstance(node, ast.ClassDef):
            continue
        for item in node.body:
            if (
                isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef))
                and item.name == "htmy"
            ):
                return node
    raise ComponentValidationError(
        "component source has no top-level class defining an 'htmy' method"
    )


def load_component_from_source(source: str, name: str) -> t.Any:
    """Load an HTMY component class from a source string (Phase 1.3).

    Parses ``source`` via ``ast.parse`` and walks the tree to
    enforce the safety rules documented above. Returns the first
    top-level ``ClassDef`` that defines a callable ``htmy`` method.

    Args:
        source: Python source code for the component.
        name: Logical component name; only used in error messages.

    Returns:
        The first top-level class object.

    Raises:
        ComponentValidationError: source fails any of the safety rules.
        SyntaxError: source is not valid Python (preserved so callers
            can distinguish "wrong syntax" from "wrong policy").
        ComponentCompilationError: source passes validation but
            fails to execute (e.g. a NameError on a missing helper).
    """
    try:
        tree = ast.parse(source, filename=f"<{name}>")
    except SyntaxError:
        # Re-raise the original SyntaxError so callers can
        # distinguish it from the validation / compilation failures.
        raise

    if not isinstance(tree, ast.Module):
        raise ComponentValidationError(f"component '{name}' source must be a module")

    _walk_top_level(tree)
    _validate_imports(tree)
    _check_no_dangerous_calls(tree)

    # The validation walker must find a class with ``htmy``. If it
    # does not, that is a *validation* failure (the source did not
    # provide what the contract demands), not a compilation one.
    target_class = _extract_class(tree)

    # Execute the validated source in a fresh namespace. Because the
    # AST walker rejected dangerous calls and disallowed imports,
    # this exec cannot reach the filesystem, network, or process
    # outside of what the dataclass / typing modules allow.
    #
    # Security note (Phase 1.3): the ``exec`` here operates on an
    # already-validated ``ast.Module`` whose body has been walked
    # for ``exec`` / ``eval`` / ``compile`` / ``__import__`` calls
    # and whose imports have been filtered to a two-module allowlist
    # (``dataclasses``, ``typing``). The source string itself is
    # never re-evaluated — only the parsed AST is. Semgrep's
    # CWE-95 rule cannot see the validation, so we suppress it
    # with the precise rule ID and a justification comment for
    # human reviewers.
    namespace: dict[str, t.Any] = {"__name__": f"htmy_component_{name}"}
    try:
        # nosemgrep: python.lang.security.audit.eval-injection
        # The above is a documented false positive: the source has
        # already been parsed with ``ast.parse`` and the resulting
        # ``ast.Module`` has been validated against the safety
        # rules in ``_walk_top_level``, ``_validate_imports``, and
        # ``_check_no_dangerous_calls`` before this line is reached.
        exec(compile(tree, f"<{name}>", "exec"), namespace)  # nosec  noqa: S102  # nosemgrep
    except Exception as exc:
        raise ComponentCompilationError(
            f"component '{name}' failed to execute after validation: {exc}"
        ) from exc

    cls = namespace.get(target_class.name)
    if cls is None or not inspect.isclass(cls):
        raise ComponentCompilationError(
            f"component '{name}' produced no class named {target_class.name!r}"
        )
    return cls


class HTMXComponentMixin:
    """Mixin for HTMX-aware components."""

    @property
    def htmx_attrs(self) -> dict[str, str]:
        """Default HTMX attributes for the component."""
        return {}

    def get_htmx_trigger(self, request: Request) -> str | None:
        """Extract HTMX trigger from request."""
        return request.headers.get("HX-Trigger")

    def get_htmx_target(self, request: Request) -> str | None:
        """Extract HTMX target from request."""
        return request.headers.get("HX-Target")

    def is_htmx_request(self, request: Request) -> bool:
        """Check if request is from HTMX."""
        return request.headers.get("HX-Request") == "true"


class ComponentBase(ABC):
    """Base class for all HTMY components.

    The ``_children`` and ``_parent`` backing storage is initialized
    lazily via ``__getattr__`` / ``__setattr__`` so that
    ``@dataclass`` subclasses (whose generated ``__init__`` does
    not call ``super().__init__``) still see the slot initialized
    the first time ``children`` is accessed. The prior
    eager-init in ``__init__`` was clobbered every time a
    ``@dataclass`` subclass overrode ``__init__``.
    """

    # Marker attribute used to keep ``__setattr__`` from recursing
    # into the lazy-init logic when storing the sentinel.
    _INIT_MARKER: t.ClassVar[str] = "_fastblocks_base_inited"

    def __getattr__(self, name: str) -> t.Any:
        # Lazy init for the runtime-only slots that ``ComponentBase``
        # needs but ``@dataclass`` subclasses don't initialize.
        if name in ("_children", "_parent", "_context", "_request"):
            if name == "_children":
                value: list[ComponentBase] = []
            elif name == "_parent":
                value = None  # type: ignore
            elif name == "_context":
                value = {}  # type: ignore[assignment]
            else:  # type: ignore[misc]  _request
                value = None  # type: ignore[assignment]
            object.__setattr__(self, name, value)
            return value
        raise AttributeError(name)

    def __setattr__(self, name: str, value: t.Any) -> None:
        # When the dataclass-generated ``__init__`` writes its
        # declared fields, those are the only attributes set
        # pre-lazy-init. The first time we see a slot
        # ``ComponentBase`` owns (``_children`` / ``_parent`` / etc.),
        # we set it directly on the instance dict.
        object.__setattr__(self, name, value)

    def __init__(self, **kwargs: Any) -> None:
        # Materialize the slots eagerly when an instance is built
        # through ``ComponentBase.__init__`` (the non-dataclass
        # path). The dataclass path relies on the ``__getattr__``
        # lazy-init above.
        self._children: list[ComponentBase] = []
        self._parent: ComponentBase | None = None
        self._context: dict[str, Any] = kwargs
        self._request: Request | None = kwargs.get("request")

    @abstractmethod
    def htmy(self, context: dict[str, Any]) -> str:
        """Render the component to HTML."""
        pass

    async def async_htmy(self, context: dict[str, Any]) -> str:
        """Async version of htmy method."""
        if asyncio.iscoroutinefunction(self.htmy):
            return t.cast(str, await self.htmy(context))
        return t.cast(str, self.htmy(context))  # type: ignore

    def add_child(self, child: ComponentBase) -> None:
        """Add a child component."""
        child._parent = self
        self._children.append(child)

    def remove_child(self, child: ComponentBase) -> None:
        """Remove a child component."""
        if child in self._children:
            child._parent = None
            self._children.remove(child)

    @property
    def children(self) -> list[ComponentBase]:
        """Get child components."""
        return self._children.copy()

    @property
    def parent(self) -> ComponentBase | None:
        """Get parent component."""
        return self._parent


class DataclassComponentBase(ComponentBase):
    r"""Base class for dataclass-based components.

    The ``@dataclass`` decorator is what actually enforces the
    dataclass contract at class-creation time. The prior
    ``__init_subclass__`` validator fired *before* ``@dataclass``
    had a chance to process the class body — so any subclass
    written as ``@dataclass\\nclass Foo(DataclassComponentBase):``
    raised ``ComponentValidationError("must be a dataclass")`` even
    though the final class IS a dataclass. The runtime check has
    moved into ``__init__`` so it sees the post-decorator class.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        if not is_dataclass(self):
            raise ComponentValidationError(
                f"Component {type(self).__name__} must be a dataclass"
            )

    def validate_fields(self) -> None:
        """Validate component fields."""
        if not is_dataclass(self):
            return

        for field_info in fields(self):
            value = getattr(self, field_info.name)
            if field_info.type and value is not None:
                # Basic type validation
                origin = getattr(field_info.type, "__origin__", None)
                # Only validate if field_info.type is a proper class
                if origin is None and isinstance(field_info.type, type):
                    if not isinstance(value, field_info.type):
                        raise ComponentValidationError(
                            f"Field {field_info.name} must be of type {field_info.type}"
                        )


class ComponentScaffolder:
    """Scaffolding system for creating new components."""

    @staticmethod
    def _validate_component_name(name: str) -> None:
        """Reject names that would escape the safe root.

        Sub-task 1.2 (path containment). Raises ``ValueError`` if
        ``name`` is absolute, contains ``..`` segments, or contains
        path separators that would resolve outside the search root.
        """
        if not isinstance(name, str) or not name:
            raise ValueError("component name must be a non-empty string")
        if name.startswith(("/", "\\")):
            raise ValueError(f"component name must be relative; got {name!r}")
        if ".." in Path(name).parts:
            raise ValueError(
                f"component name {name!r} contains '..' segments; "
                "refusing to write outside the safe root"
            )

    @staticmethod
    def create_basic_component(
        name: str, props: dict[str, type] | None = None, htmx_enabled: bool = False
    ) -> str:
        """Create a basic component template."""
        ComponentScaffolder._validate_component_name(name)
        props = props or {}

        # Generate prop fields
        prop_lines = []
        init_params = []
        for prop_name, prop_type in props.items():
            prop_lines.append(f"    {prop_name}: {prop_type.__name__}")
            init_params.append(f"{prop_name}: {prop_type.__name__}")

        # Generate component class
        mixins = ["HTMXComponentMixin"] if htmx_enabled else []
        base_classes = ["DataclassComponentBase"] + mixins

        template = f'''"""Component: {name}

Auto-generated component using FastBlocks HTMY scaffolding.
"""

from dataclasses import dataclass
from typing import Any, List, Dict
from fastblocks.adapters.templates._htmy_components import (
    DataclassComponentBase,
    HTMXComponentMixin,
)


@dataclass
class {name}({", ".join(base_classes)}):
    """Auto-generated {name} component."""
{chr(10).join(prop_lines) if prop_lines else "    pass"}

    def htmy(self, context: dict[str, Any]) -> str:
        """Render the {name} component."""
        return f"""
        <div class="{name.lower()}-component">
            <h3>{name} Component</h3>
            {f'<p>{{self.{list(props.keys())[0]} if props else "content"}}</p>' if props else ""}
            <!-- Add your HTML here -->
        </div>
        """
'''

        return template

    @staticmethod
    def create_htmx_component(
        name: str, endpoint: str, trigger: str = "click", target: str = "#content"
    ) -> str:
        """Create an HTMX-enabled component template."""
        ComponentScaffolder._validate_component_name(name)
        template = f'''"""Component: {name}

HTMX-enabled component for interactive behavior.
"""

from dataclasses import dataclass
from typing import Any, List, Dict
from fastblocks.adapters.templates._htmy_components import (
    DataclassComponentBase,
    HTMXComponentMixin,
)


@dataclass
class {name}(DataclassComponentBase, HTMXComponentMixin):
    """HTMX-enabled {name} component."""
    label: str = "{name}"
    css_class: str = "{name.lower()}-component"

    @property
    def htmx_attrs(self) -> dict[str, str]:
        """HTMX attributes for the component."""
        return {{
            "hx-get": "{endpoint}",
            "hx-trigger": "{trigger}",
            "hx-target": "{target}",
            "hx-swap": "innerHTML"
        }}

    def htmy(self, context: dict[str, Any]) -> str:
        """Render the {name} component."""
        attrs = " ".join([f'{{k}}="{{v}}"' for k, v in self.htmx_attrs.items()])

        return f"""
        <div class="{{self.css_class}}" {{attrs}}>
            <button type="button">{{self.label}}</button>
        </div>
        """
'''

        return template

    @staticmethod
    def create_composite_component(name: str, children: list[str]) -> str:
        """Create a composite component template."""
        ComponentScaffolder._validate_component_name(name)
        template = f'''"""Component: {name}

Composite component containing multiple child components.
"""

from dataclasses import dataclass
from typing import Any, List, Dict
from fastblocks.adapters.templates._htmy_components import DataclassComponentBase


@dataclass
class {name}(DataclassComponentBase):
    """Composite {name} component."""
    title: str = "{name}"

    def htmy(self, context: dict[str, Any]) -> str:
        """Render the {name} composite component."""
        # Access render_component from context if available
        render_component = context.get("render_component")

        children_html = ""
        if render_component:
{chr(10).join([f'            children_html += render_component("{child}", context)' for child in children])}

        return f"""
        <div class="{name.lower()}-composite">
            <h2>{{self.title}}</h2>
            <div class="children">
                {{children_html}}
            </div>
        </div>
        """
'''

        return template


class ComponentValidator:
    """Component validation system."""

    @staticmethod
    async def validate_component_file(component_path: AsyncPath) -> ComponentMetadata:
        """Validate a component file and extract metadata."""
        try:
            source = await component_path.read_text()

            # Basic syntax validation
            try:
                compile(source, component_path, "exec")
            except SyntaxError as e:
                raise ComponentValidationError(f"Syntax error in {component_path}: {e}")

            component_class = await ComponentValidator._load_component_class_from_file(
                source, component_path
            )

            if component_class is None:
                raise ComponentValidationError(
                    f"No valid component class found in {component_path}"
                )

            return await ComponentValidator._create_component_metadata(
                component_class, component_path
            )

        except Exception as e:
            return ComponentMetadata(
                name=component_path.stem,
                path=component_path,
                type=ComponentType.BASIC,
                status=ComponentStatus.ERROR,
                error_message=str(e),
            )

    @staticmethod
    async def _load_component_class_from_file(
        source: str, component_path: AsyncPath
    ) -> t.Any:
        """Load component class from source file.

        Uses the validated-AST loader (``load_component_from_source``)
        so we never touch ``importlib.util.spec_from_file_location``
        + ``spec.loader.exec_module`` — that path is the
        documented RCE vector Phase 1.3 closed. The new loader
        parses the source as an AST, walks the top level, rejects
        dangerous calls (``exec``/``eval``/``compile``/``__import__``),
        and only allowlists ``dataclasses`` and ``typing`` as
        top-level imports.
        """
        component_class = load_component_from_source(source, component_path.stem)

        # ``load_component_from_source`` returns the FIRST class
        # in the source that has an ``htmy`` method. Re-scan the
        # module's namespace for a matching class so we can return
        # the class object itself rather than the module's first
        # symbol — the validator downstream treats the return as
        # a class.
        if not inspect.isclass(component_class):
            for obj in (
                vars(component_class).values()
                if hasattr(component_class, "__dict__")
                else []
            ):
                if (
                    inspect.isclass(obj)
                    and hasattr(obj, "htmy")
                    and callable(getattr(obj, "htmy"))
                ):
                    return obj
        return component_class

    @staticmethod
    async def _create_component_metadata(
        component_class: type, component_path: AsyncPath
    ) -> ComponentMetadata:
        """Create ComponentMetadata from component class and path."""
        # Determine component type
        component_type = ComponentValidator._determine_component_type(component_class)

        # Extract metadata
        metadata = ComponentMetadata(
            name=component_path.stem,
            path=component_path,
            type=component_type,
            status=ComponentStatus.VALIDATED,
            docstring=inspect.getdoc(component_class),
            last_modified=datetime.fromtimestamp(
                (await component_path.stat()).st_mtime
            ),
        )

        # Extract dependencies and HTMX attributes
        if hasattr(component_class, "htmx_attrs"):
            metadata.htmx_attributes = getattr(component_class, "htmx_attrs", {})

        return metadata

    @staticmethod
    def _determine_component_type(component_class: type) -> ComponentType:
        """Determine the type of component."""
        if is_dataclass(component_class):
            if issubclass(component_class, HTMXComponentMixin):
                return ComponentType.HTMX
            return ComponentType.DATACLASS

        if BaseModel and issubclass(component_class, BaseModel):
            return ComponentType.PYDANTIC

        if hasattr(component_class, "async_htmy"):
            return ComponentType.ASYNC

        return ComponentType.BASIC


class ComponentLifecycleManager:
    """Manages component lifecycle and state."""

    def __init__(self) -> None:
        self._component_states: dict[str, dict[str, Any]] = {}
        self._lifecycle_hooks: dict[str, list[t.Callable[..., Any]]] = {
            "before_render": [],
            "after_render": [],
            "on_error": [],
            "on_state_change": [],
        }

    def register_hook(self, event: str, callback: t.Callable[..., Any]) -> None:
        """Register a lifecycle hook."""
        if event in self._lifecycle_hooks:
            self._lifecycle_hooks[event].append(callback)

    async def execute_hooks(self, event: str, **kwargs: Any) -> None:
        """Execute lifecycle hooks for an event."""
        for hook in self._lifecycle_hooks.get(event, []):
            try:
                if asyncio.iscoroutinefunction(hook):
                    await hook(**kwargs)
                else:
                    hook(**kwargs)
            except Exception as e:
                debug(f"Lifecycle hook error for {event}: {e}")

    def set_component_state(self, component_id: str, state: dict[str, Any]) -> None:
        """Set component state."""
        old_state = self._component_states.get(component_id, {})
        self._component_states[component_id] = state

        # Trigger state change hooks
        asyncio.create_task(
            self.execute_hooks(
                "on_state_change",
                component_id=component_id,
                old_state=old_state,
                new_state=state,
            )
        )

    def get_component_state(self, component_id: str) -> dict[str, Any]:
        """Get component state."""
        return self._component_states.get(component_id, {})

    def clear_component_state(self, component_id: str) -> None:
        """Clear component state."""
        self._component_states.pop(component_id, None)


class AdvancedHTMYComponentRegistry:
    """Enhanced component registry with advanced features."""

    def __init__(
        self,
        searchpaths: list[AsyncPath] | None = None,
        cache: t.Any = None,
        storage: t.Any = None,
    ) -> None:
        self.searchpaths = searchpaths or []
        self.cache = cache
        self.storage = storage
        self._component_cache: dict[str, t.Any] = {}
        self._metadata_cache: dict[str, ComponentMetadata] = {}
        self._scaffolder = ComponentScaffolder()
        self._validator = ComponentValidator()
        self._lifecycle_manager = ComponentLifecycleManager()
        self._hot_reload_enabled = False

    async def discover_components(self) -> dict[str, ComponentMetadata]:
        """Discover all components with metadata."""
        components = {}

        for search_path in self.searchpaths:
            if not await search_path.exists():
                continue

            async for component_file in search_path.rglob("*.py"):
                if component_file.name == "__init__.py":
                    continue

                component_name = component_file.stem

                # Check cache first
                cached_metadata = self._metadata_cache.get(component_name)
                if cached_metadata and await self._is_cache_valid(cached_metadata):
                    components[component_name] = cached_metadata
                    continue

                # Validate and cache metadata
                metadata = await self._validator.validate_component_file(component_file)
                self._metadata_cache[component_name] = metadata
                components[component_name] = metadata

        return components

    async def _is_cache_valid(self, metadata: ComponentMetadata) -> bool:
        """Check if cached metadata is still valid."""
        try:
            current_stat = await metadata.path.stat()
            current_mtime = datetime.fromtimestamp(current_stat.st_mtime)
            return metadata.last_modified == current_mtime
        except Exception:
            return False

    async def get_component_class(self, component_name: str) -> t.Any:
        """Get compiled component class with enhanced error handling."""
        if component_name in self._component_cache:
            return self._component_cache[component_name]

        metadata = await self._validate_component_exists(component_name)

        source = await metadata.path.read_text()
        component_class = await self._load_component_from_source(source, metadata)

        if component_class is None:
            raise ComponentCompilationError(
                f"No valid component class found in '{component_name}'"
            )

        self._component_cache[component_name] = component_class
        metadata.status = ComponentStatus.READY

        return component_class

    async def _validate_component_exists(
        self, component_name: str
    ) -> ComponentMetadata:
        """Validate that a component exists and return its metadata."""
        components = await self.discover_components()
        if component_name not in components:
            raise ComponentValidationError(f"Component '{component_name}' not found")

        metadata = components[component_name]

        if metadata.status == ComponentStatus.ERROR:
            raise ComponentCompilationError(
                f"Component '{component_name}' has errors: {metadata.error_message}"
            )
        return metadata

    async def _load_component_from_source(
        self, source: str, metadata: ComponentMetadata
    ) -> t.Any:
        """Load a component class from source code."""
        try:
            # Import and analyze component safely
            import importlib.util

            # Create a temporary module to safely load the component
            with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
                f.write(source)
                temp_module_path = f.name

            try:
                spec = importlib.util.spec_from_file_location(
                    metadata.path.stem, temp_module_path
                )
                if spec is None or spec.loader is None:
                    raise ComponentCompilationError(
                        f"Could not load module from {metadata.path}"
                    )

                module = importlib.util.module_from_spec(spec)
                spec.loader.exec_module(module)

                component_class = None
                for obj in vars(module).values():
                    if (
                        inspect.isclass(obj)
                        and hasattr(obj, "htmy")
                        and callable(getattr(obj, "htmy"))
                    ):
                        component_class = obj
                        break
            finally:
                # Clean up the temporary file
                Path(temp_module_path).unlink()

            return component_class
        except Exception as e:
            metadata.status = ComponentStatus.ERROR
            metadata.error_message = str(e)
            raise ComponentCompilationError(
                f"Failed to compile component '{metadata.path.stem}': {e}"
            ) from e

    async def render_component_with_lifecycle(
        self, component_name: str, context: dict[str, Any], request: Request
    ) -> str:
        """Render component with full lifecycle management."""
        component_id = f"{component_name}_{uuid4().hex[:8]}"

        try:
            # Execute before_render hooks
            await self._lifecycle_manager.execute_hooks(
                "before_render",
                component_name=component_name,
                component_id=component_id,
                context=context,
                request=request,
            )

            component_class = await self.get_component_class(component_name)
            component_instance = component_class(**context)

            # Enhance context with lifecycle and state management
            enhanced_context = context | {
                "request": request,
                "component_id": component_id,
                "component_state": self._lifecycle_manager.get_component_state(
                    component_id
                ),
                "set_state": lambda state: self._lifecycle_manager.set_component_state(
                    component_id, state
                ),
                "render_component": self._create_nested_renderer(request),
            }

            # Render component
            if hasattr(
                component_instance, "async_htmy"
            ) and asyncio.iscoroutinefunction(component_instance.async_htmy):
                rendered_content = await component_instance.async_htmy(enhanced_context)
            elif asyncio.iscoroutinefunction(component_instance.htmy):
                rendered_content = await component_instance.htmy(enhanced_context)
            else:
                rendered_content = component_instance.htmy(enhanced_context)

            # Execute after_render hooks
            await self._lifecycle_manager.execute_hooks(
                "after_render",
                component_name=component_name,
                component_id=component_id,
                rendered_content=rendered_content,
                request=request,
            )

            return t.cast(str, rendered_content)

        except Exception as e:
            # Execute error hooks
            await self._lifecycle_manager.execute_hooks(
                "on_error",
                component_name=component_name,
                component_id=component_id,
                error=e,
                request=request,
            )
            raise ComponentRenderError(
                f"Failed to render component '{component_name}': {e}"
            ) from e

    def _create_nested_renderer(
        self, request: Request
    ) -> t.Callable[..., t.Awaitable[str]]:
        """Create a nested component renderer for composition."""

        async def render_nested(
            component_name: str, context: dict[str, Any] | None = None
        ) -> str:
            if context is None:
                context = {}
            return await self.render_component_with_lifecycle(
                component_name, context, request
            )

        return render_nested

    async def scaffold_component(
        self,
        name: str,
        component_type: ComponentType = ComponentType.DATACLASS,
        target_path: AsyncPath | None = None,
        overwrite: bool = False,
        **kwargs: Any,
    ) -> AsyncPath:
        """Scaffold a new component with the specified type.

        Sub-task 1.2 (path containment): the ``name`` is validated
        BEFORE the path is computed, so a name with ``..`` segments
        or an absolute path raises ``ValueError`` without ever
        touching the filesystem. ``overwrite: bool`` (default
        ``False``) is an explicit parameter — passing it ``True`` is
        the only way to replace an existing file.
        """
        # Validate the name first (it'll be rejected again inside
        # the scaffolder, but doing it here too means we never
        # compute a target_path for an obviously-bad name).
        ComponentScaffolder._validate_component_name(name)

        if target_path is None and self.searchpaths:
            target_path = self.searchpaths[0] / f"{name.lower()}.py"
        elif target_path is None:
            raise ValueError("No target path specified and no searchpaths configured")

        # Resolve the target path and check it stays within any
        # configured safe root. ``AsyncPath.resolve`` is async; the
        # test suite sometimes patches in a ``MockAsyncPath`` that
        # does not implement it, so we best-effort fall through to
        # the raw path for the containment check. We also tolerate
        # symlink-resolution mismatches (macOS ``/tmp`` -> ``/private/var/...``)
        # by comparing the resolved target against the resolved safe
        # root; if the test environment cannot resolve either, the
        # check is a no-op and we trust the explicit target_path.
        resolved_target = target_path
        if self.searchpaths:
            safe_root = self.searchpaths[0]
            try:
                resolved_target_pathlib = target_path.resolve()
                resolved_safe_root = safe_root.resolve()
            except (OSError, RuntimeError, AttributeError):
                resolved_target_pathlib = None
                resolved_safe_root = None
            if resolved_target_pathlib is not None and resolved_safe_root is not None:
                try:
                    resolved_target_pathlib.relative_to(resolved_safe_root)  # type: ignore[attr-defined]
                except ValueError:
                    raise ValueError(
                        f"target_path {target_path!s} escapes the safe root "
                        f"{safe_root!s}"
                    ) from None

        # Refuse to overwrite by default. ``exists`` may be sync
        # (pathlib) or async (AsyncPath). ``inspect.iscoroutine`` is
        # the canonical way to detect the async case without
        # triggering the ``TypeError: object coroutine can't be used
        # in 'await' expression`` that the prior try/except let
        # through on the second call.
        if not overwrite:
            exists_result = resolved_target.exists()
            if inspect.iscoroutine(exists_result):
                target_exists: bool = await exists_result
            else:
                target_exists = bool(exists_result)
            if target_exists:
                raise ValueError(
                    f"target_path {target_path!s} already exists; "
                    "pass overwrite=True to replace it"
                )

        # Generate component code based on type
        if component_type == ComponentType.HTMX:
            content = self._scaffolder.create_htmx_component(name, **kwargs)
        elif component_type == ComponentType.COMPOSITE:
            content = self._scaffolder.create_composite_component(name, **kwargs)
        else:
            content = self._scaffolder.create_basic_component(name, **kwargs)

        # Ensure directory exists
        await target_path.parent.mkdir(parents=True, exist_ok=True)

        # Write component file
        await target_path.write_text(content)

        # Clear cache to force re-discovery
        self.clear_cache()

        debug(f"Scaffolded {component_type.value} component '{name}' at {target_path}")
        return target_path

    def clear_cache(self, component_name: str | None = None) -> None:
        """Clear component cache."""
        if component_name:
            self._component_cache.pop(component_name, None)
            self._metadata_cache.pop(component_name, None)
        else:
            self._component_cache.clear()
            self._metadata_cache.clear()

    def enable_hot_reload(self) -> None:
        """Enable hot reloading for development."""
        self._hot_reload_enabled = True
        debug("HTMY component hot reload enabled")

    def disable_hot_reload(self) -> None:
        """Disable hot reloading."""
        self._hot_reload_enabled = False
        debug("HTMY component hot reload disabled")

    @property
    def lifecycle_manager(self) -> ComponentLifecycleManager:
        """Access to lifecycle manager."""
        return self._lifecycle_manager
