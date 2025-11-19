"""Advanced Template Management System for FastBlocks Week 7-8.

This module provides advanced Jinja2 template management with enhanced features:
- Template syntax checking and validation with line-by-line error reporting
- Fragment and partial template support for HTMX
- Template variable autocomplete for adapter functions
- Enhanced security with sandboxed environments
- Performance optimization with advanced caching
- Context-aware template suggestions

Requirements:
- jinja2>=3.1.6
- jinja2-async-environment>=0.14.3
- starlette-async-jinja>=1.12.4

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import asyncio
import re
import typing as t
from contextlib import suppress
from dataclasses import dataclass, field
from enum import Enum
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import depends
from jinja2 import (
    Environment,
    StrictUndefined,
    Template,
    TemplateError,
    TemplateNotFound,
    TemplateSyntaxError,
    UndefinedError,
    meta,
)

try:
    from jinja2.sandbox import SandboxedEnvironment
except ImportError:
    # Fallback for older Jinja2 versions
    SandboxedEnvironment = Environment  # type: ignore[no-redef]
from jinja2.runtime import StrictUndefined as RuntimeStrictUndefined

from .jinja2 import Templates, TemplatesSettings

__all__ = [
    "HybridTemplatesManager",
    "HybridTemplatesSettings",
    "AutocompleteItem",
    "FragmentInfo",
    "SecurityLevel",
    "TemplateError",
    "TemplateValidationResult",
    "ValidationLevel",
]

# Module-level constants for autocomplete data
_JINJA2_BUILTIN_FILTERS = [
    ("abs", "filter", "Return absolute value", "number|abs"),
    ("attr", "filter", "Get attribute by name", "obj|attr('name')"),
    ("batch", "filter", "Batch items into sublists", "items|batch(3)"),
    ("capitalize", "filter", "Capitalize first letter", "text|capitalize"),
    ("center", "filter", "Center text in field", "text|center(80)"),
    ("default", "filter", "Default value if undefined", "var|default('fallback')"),
    ("dictsort", "filter", "Sort dict by key/value", "dict|dictsort"),
    ("escape", "filter", "Escape HTML characters", "text|escape"),
    ("filesizeformat", "filter", "Format file size", "bytes|filesizeformat"),
    ("first", "filter", "Get first item", "items|first"),
    ("float", "filter", "Convert to float", "value|float"),
    ("format", "filter", "String formatting", "'{0}'.format(value)"),
    ("groupby", "filter", "Group by attribute", "items|groupby('category')"),
    ("indent", "filter", "Indent text", "text|indent(4)"),
    ("int", "filter", "Convert to integer", "value|int"),
    ("join", "filter", "Join list with separator", "items|join(', ')"),
    ("last", "filter", "Get last item", "items|last"),
    ("length", "filter", "Get length", "items|length"),
    ("list", "filter", "Convert to list", "value|list"),
    ("lower", "filter", "Convert to lowercase", "text|lower"),
    ("map", "filter", "Apply filter to each item", "items|map('upper')"),
    ("max", "filter", "Get maximum value", "numbers|max"),
    ("min", "filter", "Get minimum value", "numbers|min"),
    ("random", "filter", "Get random item", "items|random"),
    ("reject", "filter", "Reject items by test", "items|reject('odd')"),
    ("replace", "filter", "Replace substring", "text|replace('old', 'new')"),
    ("reverse", "filter", "Reverse order", "items|reverse"),
    ("round", "filter", "Round number", "number|round(2)"),
    ("safe", "filter", "Mark as safe HTML", "html|safe"),
    ("select", "filter", "Select items by test", "items|select('even')"),
    ("slice", "filter", "Slice sequence", "items|slice(3)"),
    ("sort", "filter", "Sort items", "items|sort"),
    ("string", "filter", "Convert to string", "value|string"),
    ("striptags", "filter", "Remove HTML tags", "html|striptags"),
    ("sum", "filter", "Sum numeric values", "numbers|sum"),
    ("title", "filter", "Title case", "text|title"),
    ("trim", "filter", "Strip whitespace", "text|trim"),
    ("truncate", "filter", "Truncate text", "text|truncate(50)"),
    ("unique", "filter", "Remove duplicates", "items|unique"),
    ("upper", "filter", "Convert to uppercase", "text|upper"),
    ("urlencode", "filter", "URL encode", "text|urlencode"),
    ("urlize", "filter", "Convert URLs to links", "text|urlize"),
    ("wordcount", "filter", "Count words", "text|wordcount"),
    ("wordwrap", "filter", "Wrap text", "text|wordwrap(80)"),
]

_JINJA2_BUILTIN_FUNCTIONS = [
    (
        "range",
        "function",
        "Generate sequence of numbers",
        "range(10)",
        "range(start, stop, step)",
    ),
    (
        "lipsum",
        "function",
        "Generate lorem ipsum text",
        "lipsum(5)",
        "lipsum(n=5, html=True, min=20, max=100)",
    ),
    ("dict", "function", "Create dictionary", "dict(key='value')", "dict(**kwargs)"),
    (
        "cycler",
        "function",
        "Create value cycler",
        "cycler('odd', 'even')",
        "cycler(*items)",
    ),
    ("joiner", "function", "Create joiner helper", "joiner(', ')", "joiner(sep=', ')"),
]

_ADAPTER_AUTOCOMPLETE_FUNCTIONS = {
    "images": ["get_image_url", "get_img_tag", "get_placeholder_url"],
    "icons": ["get_icon_tag", "get_icon_with_text"],
    "fonts": ["get_font_import", "get_font_family"],
    "styles": [
        "get_component_class",
        "get_utility_classes",
        "build_component_html",
    ],
}


class ValidationLevel(Enum):
    """Template validation levels."""

    SYNTAX_ONLY = "syntax_only"
    VARIABLES = "variables"
    FULL = "full"


class SecurityLevel(Enum):
    """Template security levels."""

    STANDARD = "standard"
    RESTRICTED = "restricted"
    SANDBOXED = "sandboxed"


@dataclass
class TemplateValidationError:
    """Represents a template validation error."""

    message: str
    line_number: int | None = None
    column_number: int | None = None
    error_type: str = "validation"
    severity: str = "error"  # error, warning, info
    template_name: str | None = None
    context: str | None = None  # surrounding code context


@dataclass
class TemplateValidationResult:
    """Result of template validation."""

    is_valid: bool
    errors: list[TemplateValidationError] = field(default_factory=list)
    warnings: list[TemplateValidationError] = field(default_factory=list)
    suggestions: list[str] = field(default_factory=list)
    used_variables: set[str] = field(default_factory=set)
    undefined_variables: set[str] = field(default_factory=set)
    available_filters: set[str] = field(default_factory=set)
    available_functions: set[str] = field(default_factory=set)


@dataclass
class FragmentInfo:
    """Information about a template fragment."""

    name: str
    template_path: str
    block_name: str | None = None
    start_line: int | None = None
    end_line: int | None = None
    variables: set[str] = field(default_factory=set)
    dependencies: set[str] = field(default_factory=set)


@dataclass
class AutocompleteItem:
    """Autocomplete suggestion item."""

    name: str
    type: str  # variable, filter, function, block
    description: str | None = None
    signature: str | None = None
    adapter_source: str | None = None
    example: str | None = None


def _default_sandbox_attributes() -> list[str]:
    """Get default allowed sandbox attributes."""
    return [
        "alt",
        "class",
        "id",
        "src",
        "href",
        "title",
        "width",
        "height",
    ]


def _default_sandbox_tags() -> list[str]:
    """Get default allowed sandbox tags."""
    return [
        "div",
        "span",
        "p",
        "a",
        "img",
        "h1",
        "h2",
        "h3",
        "h4",
        "h5",
        "h6",
        "ul",
        "ol",
        "li",
        "strong",
        "em",
        "br",
        "hr",
    ]


class HybridTemplatesSettings(TemplatesSettings):
    """Advanced template settings with enhanced features."""

    # Validation settings
    validation_level: ValidationLevel = ValidationLevel.VARIABLES
    validate_on_load: bool = True
    strict_undefined: bool = True

    # Security settings
    security_level: SecurityLevel = SecurityLevel.STANDARD
    sandbox_allowed_attributes: list[str] = field(
        default_factory=_default_sandbox_attributes
    )
    sandbox_allowed_tags: list[str] = field(default_factory=_default_sandbox_tags)

    # Fragment/Partial settings
    enable_fragments: bool = True
    fragment_prefix: str = "_"
    auto_discover_fragments: bool = True

    # Autocomplete settings
    enable_autocomplete: bool = True
    scan_adapter_functions: bool = True
    cache_autocomplete: bool = True

    # Performance settings
    enable_template_cache: bool = True
    template_cache_size: int = 1000
    enable_compiled_cache: bool = True
    precompile_templates: bool = False

    # Advanced error handling
    detailed_errors: bool = True
    show_context_lines: int = 3
    enable_error_suggestions: bool = True

    def __init__(self, **data: t.Any) -> None:
        super().__init__(**data)


class HybridTemplatesManager:
    """Advanced template management with validation, fragments, and autocomplete."""

    def __init__(self, settings: HybridTemplatesSettings | None = None) -> None:
        self.settings = settings or HybridTemplatesSettings()
        self.base_templates: Templates | None = None
        self._validation_cache: dict[str, TemplateValidationResult] = {}
        self._fragment_cache: dict[str, list[FragmentInfo]] = {}
        self._autocomplete_cache: dict[str, list[AutocompleteItem]] = {}
        self._template_dependencies: dict[str, set[str]] = {}

    async def _initialize_base_templates(self) -> None:
        """Initialize base templates instance."""
        try:
            self.base_templates = depends.get("templates")
        except Exception:
            self.base_templates = Templates()
            if not self.base_templates.app:
                await self.base_templates.init()

    async def _initialize_advanced_features(self) -> None:
        """Initialize advanced template features."""
        if self.settings.enable_fragments:
            await self._discover_fragments()

        if self.settings.enable_autocomplete:
            await self._build_autocomplete_index()

    async def initialize(self) -> None:
        """Initialize the advanced template manager."""
        await self._initialize_base_templates()
        await self._initialize_advanced_features()

    def _get_template_environment(self, secure: bool = False) -> Environment:
        """Get Jinja2 environment with appropriate security settings."""
        if not self.base_templates or not self.base_templates.app:
            raise RuntimeError("Base templates not initialized")

        env = self.base_templates.app.env

        if secure and self.settings.security_level == SecurityLevel.SANDBOXED:
            # Create sandboxed environment
            sandbox_env = SandboxedEnvironment(
                loader=env.loader,
                extensions=t.cast(t.Any, list(env.extensions.values())),
                undefined=StrictUndefined
                if self.settings.strict_undefined
                else RuntimeStrictUndefined,
            )

            # Apply security restrictions (Jinja2 sandbox API)
            sandbox_env.allowed_tags = set(self.settings.sandbox_allowed_tags)  # type: ignore[attr-defined]
            sandbox_env.allowed_attributes = set(  # type: ignore[attr-defined]
                self.settings.sandbox_allowed_attributes
            )

            return sandbox_env

        return t.cast(Environment, env)

    async def validate_template(
        self,
        template_source: str,
        template_name: str = "unknown",
        context: dict[str, t.Any] | None = None,
    ) -> TemplateValidationResult:
        """Validate template syntax and variables with detailed error reporting."""
        # Check cache first
        cache_key = f"{template_name}:{hash(template_source)}"
        if cache_key in self._validation_cache:
            return self._validation_cache[cache_key]

        result = TemplateValidationResult(is_valid=True)
        env = self._get_template_environment()

        try:
            # Parse template for syntax validation
            parsed = env.parse(template_source, template_name)

            # Extract variables and blocks
            used_vars = meta.find_undeclared_variables(parsed)
            result.used_variables = used_vars

            # Get available variables from context and adapters
            available_vars = self._get_available_variables(context)
            result.undefined_variables = used_vars - available_vars

            # Get available filters and functions
            result.available_filters = set(env.filters.keys())
            result.available_functions = set(env.globals.keys())

            # Validate variables if required
            if self.settings.validation_level in (
                ValidationLevel.VARIABLES,
                ValidationLevel.FULL,
            ):
                await self._validate_variables(result, template_source, template_name)

            # Full validation includes template compilation
            if self.settings.validation_level == ValidationLevel.FULL:
                await self._validate_compilation(
                    result, template_source, template_name, env
                )

        except TemplateSyntaxError as e:
            result.is_valid = False
            error = TemplateValidationError(
                message=str(e),
                line_number=e.lineno,
                error_type="syntax",
                template_name=template_name,
                context=self._get_error_context(template_source, e.lineno),
            )
            result.errors.append(error)

        except Exception as e:
            result.is_valid = False
            error = TemplateValidationError(
                message=f"Validation error: {e}",
                error_type="general",
                template_name=template_name,
            )
            result.errors.append(error)

        # Add suggestions for improvements
        if self.settings.enable_error_suggestions:
            await self._add_suggestions(result, template_source)

        # Cache result
        self._validation_cache[cache_key] = result
        return result

    @staticmethod
    def _get_available_variables(context: dict[str, t.Any] | None = None) -> set[str]:
        """Get all available variables from context and adapters."""
        available = set()

        # Add context variables
        if context:
            available.update(context.keys())

        # Add adapter variables
        available.update(
            ["config", "request", "models", "render_block", "render_component"]
        )

        # Add adapter functions
        with suppress(Exception):
            for adapter_name in (
                "images",
                "icons",
                "fonts",
                "styles",
                "cache",
                "storage",
            ):
                with suppress(Exception):
                    adapter = depends.get_sync(adapter_name)
                    if adapter:
                        available.add(adapter_name)

        return available

    async def _validate_variables(
        self, result: TemplateValidationResult, template_source: str, template_name: str
    ) -> None:
        """Validate variable usage in template."""
        lines = template_source.split("\n")

        for line_num, line in enumerate(lines, 1):
            # Find variable usage patterns
            var_pattern = re.compile(
                r"\[\[\s*([^|\[\]]+?)(?:\s*\|[^|\[\]]*?)?\s*\]\]"
            )  # REGEX OK: FastBlocks template variable syntax
            matches = var_pattern.finditer(line)

            for match in matches:
                var_expr = match.group(1).strip()
                base_var = var_expr.split(".")[0].split("(")[0].strip()

                if base_var in result.undefined_variables:
                    error = TemplateValidationError(
                        message=f"Undefined variable: {base_var}",
                        line_number=line_num,
                        column_number=match.start(),
                        error_type="undefined_variable",
                        severity="warning"
                        if self._is_safe_undefined(base_var)
                        else "error",
                        template_name=template_name,
                        context=line.strip(),
                    )

                    if error.severity == "error":
                        result.errors.append(error)
                        result.is_valid = False
                    else:
                        result.warnings.append(error)

    def _is_safe_undefined(self, var_name: str) -> bool:
        """Check if undefined variable is potentially safe (like optional context)."""
        safe_patterns = ["user", "session", "flash", "messages", "csrf_token"]
        return any(pattern in var_name.lower() for pattern in safe_patterns)

    async def _validate_compilation(
        self,
        result: TemplateValidationResult,
        template_source: str,
        template_name: str,
        env: Environment,
    ) -> None:
        """Validate template compilation with mock context."""
        try:
            template = env.from_string(template_source, template_class=Template)

            # Create mock context for testing
            mock_context = self._create_mock_context(result.used_variables)

            # Try to render with mock context
            await asyncio.get_event_loop().run_in_executor(
                None, template.render, mock_context
            )

        except UndefinedError:
            # This is expected for some undefined variables
            pass
        except Exception as e:
            result.is_valid = False
            error = TemplateValidationError(
                message=f"Compilation error: {e}",
                error_type="compilation",
                template_name=template_name,
            )
            result.errors.append(error)

    def _create_mock_context(self, variables: set[str]) -> dict[str, t.Any]:
        """Create mock context for template validation."""
        mock_context: dict[str, t.Any] = {}

        for var in variables:
            if "." in var:
                # Handle nested variables
                parts = var.split(".")
                current = mock_context
                for part in parts[:-1]:
                    if part not in current:
                        current[part] = {}
                    current = current[part]
                current[parts[-1]] = "mock_value"
            else:
                mock_context[var] = "mock_value"

        return mock_context

    def _get_error_context(
        self, template_source: str, line_number: int | None
    ) -> str | None:
        """Get surrounding lines for error context."""
        if not line_number or not self.settings.detailed_errors:
            return None

        lines = template_source.split("\n")
        start = max(0, line_number - self.settings.show_context_lines - 1)
        end = min(len(lines), line_number + self.settings.show_context_lines)

        context_lines = []
        for i in range(start, end):
            marker = ">>> " if i == line_number - 1 else "    "
            context_lines.append(f"{marker}{i + 1:4d}: {lines[i]}")

        return "\n".join(context_lines)

    async def _add_suggestions(
        self, result: TemplateValidationResult, template_source: str
    ) -> None:
        """Add helpful suggestions for template improvements."""
        suggestions = []

        # Suggest available alternatives for undefined variables
        for undefined_var in result.undefined_variables:
            available = result.used_variables - result.undefined_variables

            # Simple fuzzy matching for suggestions
            for var in available:
                if self._is_similar(undefined_var, var):
                    suggestions.append(
                        f"Did you mean '{var}' instead of '{undefined_var}'?"
                    )
                    break

        # Suggest filters for common patterns
        if "| safe" not in template_source and any(
            tag in template_source for tag in ("<", ">")
        ):
            suggestions.append("Consider using the '| safe' filter for HTML content")

        # Suggest async patterns for image operations
        if "image_url(" in template_source and "await" not in template_source:
            suggestions.append(
                "Consider using 'await async_image_url()' for better performance"
            )

        result.suggestions.extend(suggestions)

    def _is_similar(self, a: str, b: str, threshold: float = 0.6) -> bool:
        """Simple string similarity check."""
        if not a or not b:
            return False

        # Levenshtein distance approximation
        longer = a if len(a) > len(b) else b
        shorter = b if len(a) > len(b) else a

        if not longer:
            return True

        # Simple similarity based on common characters
        common = sum(1 for char in shorter if char in longer)
        similarity = common / len(longer)

        return similarity >= threshold

    async def _discover_fragments(self) -> None:
        """Discover and index template fragments for HTMX support."""
        if not self.base_templates:
            return

        # Get all template paths
        env = self._get_template_environment()
        if not env.loader:
            return

        try:
            template_names = await asyncio.get_event_loop().run_in_executor(
                None, env.loader.list_templates
            )
        except Exception:
            return

        for template_name in template_names:
            if template_name.startswith(self.settings.fragment_prefix):
                await self._analyze_fragment(template_name)

    async def _analyze_fragment(self, template_name: str) -> None:
        """Analyze a template fragment and extract metadata."""
        with suppress(Exception):
            env = self._get_template_environment()
            source, _, _ = env.loader.get_source(env, template_name)  # type: ignore[union-attr,misc]

            # Parse template to find blocks
            parsed = env.parse(source, template_name)

            fragments = []

            # Extract block information
            for node in parsed.body:
                if hasattr(node, "name") and node.name:  # type: ignore[attr-defined]
                    fragment = FragmentInfo(
                        name=node.name,  # type: ignore[attr-defined]
                        template_path=template_name,
                        block_name=node.name,  # type: ignore[attr-defined]
                        start_line=getattr(node, "lineno", None),
                    )

                    # Find variables used in this fragment
                    fragment.variables = meta.find_undeclared_variables(parsed)
                    fragments.append(fragment)

            # If no blocks found, treat entire template as fragment
            if not fragments:
                fragment = FragmentInfo(
                    name=template_name.replace(".html", "").replace(
                        self.settings.fragment_prefix, ""
                    ),
                    template_path=template_name,
                    variables=meta.find_undeclared_variables(parsed),
                )
                fragments.append(fragment)

            self._fragment_cache[template_name] = fragments

    async def _build_autocomplete_index(self) -> None:
        """Build autocomplete index for template variables and functions."""
        autocomplete_items = []

        # Add built-in Jinja2 items
        autocomplete_items.extend(self._get_builtin_autocomplete())

        # Add adapter functions if enabled
        if self.settings.scan_adapter_functions:
            autocomplete_items.extend(await self._get_adapter_autocomplete())

        # Add template-specific items
        autocomplete_items.extend(self._get_template_autocomplete())

        # Cache the results
        cache_key = "global"
        self._autocomplete_cache[cache_key] = autocomplete_items

    def _get_builtin_autocomplete(self) -> list[AutocompleteItem]:
        """Get autocomplete items for built-in Jinja2 features."""
        # Add filters from module constant using list comprehension
        items = [
            AutocompleteItem(
                name=name,
                type=item_type,
                description=description,
                example=example,
                adapter_source="jinja2",
            )
            for name, item_type, description, example in _JINJA2_BUILTIN_FILTERS
        ]

        # Add functions from module constant using list comprehension
        items.extend(
            AutocompleteItem(
                name=name,
                type=item_type,
                description=description,
                signature=signature,
                example=example,
                adapter_source="jinja2",
            )
            for name, item_type, description, example, signature in _JINJA2_BUILTIN_FUNCTIONS
        )

        return items

    def _add_filter_items(
        self, items: list[AutocompleteItem], filters: dict[str, t.Any], filter_type: str
    ) -> None:
        """Add filter autocomplete items from filter dictionary."""
        for name, func in filters.items():
            doc = func.__doc__ or ""
            description = (
                doc.split("\n")[0] if doc else f"FastBlocks {name} {filter_type}"
            )

            items.append(
                AutocompleteItem(
                    name=name,
                    type="filter",
                    description=description,
                    adapter_source="fastblocks",
                    example=self._extract_example_from_doc(doc),
                )
            )

    @staticmethod
    def _add_adapter_function_items(items: list[AutocompleteItem]) -> None:
        """Add adapter function autocomplete items."""
        for adapter_name, functions in _ADAPTER_AUTOCOMPLETE_FUNCTIONS.items():
            with suppress(Exception):
                adapter = depends.get_sync(adapter_name)
                if adapter:
                    for func_name in functions:
                        if hasattr(adapter, func_name):
                            items.append(
                                AutocompleteItem(
                                    name=f"{adapter_name}.{func_name}",
                                    type="function",
                                    description=f"{adapter_name.title()} adapter function",
                                    adapter_source=adapter_name,
                                )
                            )

    async def _get_adapter_autocomplete(self) -> list[AutocompleteItem]:
        """Get autocomplete items for adapter functions."""
        items: list[AutocompleteItem] = []

        # FastBlocks-specific filters from our filter modules
        from ._async_filters import FASTBLOCKS_ASYNC_FILTERS
        from ._filters import FASTBLOCKS_FILTERS

        # Add sync filters
        self._add_filter_items(items, FASTBLOCKS_FILTERS, "filter")

        # Add async filters
        self._add_filter_items(items, FASTBLOCKS_ASYNC_FILTERS, "async filter")

        # Add adapter-specific functions
        self._add_adapter_function_items(items)

        return items

    @staticmethod
    def _get_template_autocomplete() -> list[AutocompleteItem]:
        """Get autocomplete items for template-specific variables."""
        items = []

        # Common template variables
        common_vars = [
            ("config", "variable", "Application configuration object"),
            ("request", "variable", "Current HTTP request object"),
            ("models", "variable", "Database models"),
            ("render_block", "function", "Render template block"),
            ("render_component", "function", "Render HTMY component"),
        ]

        for name, item_type, description in common_vars:
            items.append(
                AutocompleteItem(
                    name=name,
                    type=item_type,
                    description=description,
                    adapter_source="fastblocks",
                )
            )

        return items

    def _extract_example_from_doc(self, doc: str) -> str | None:
        """Extract usage example from docstring."""
        if not doc:
            return None

        lines = doc.split("\n")
        in_example = False
        example_lines = []

        for line in lines:
            line = line.strip()
            if line.startswith("[[ ") and line.endswith(" ]]"):
                return line
            elif "Usage:" in line or "Example:" in line:
                in_example = True
            elif in_example and line.startswith("[["):
                example_lines.append(line)
            elif in_example and line and not line.startswith(" "):
                break

        return example_lines[0] if example_lines else None

    async def get_fragments_for_template(
        self, template_name: str
    ) -> list[FragmentInfo]:
        """Get fragments available for a specific template."""
        if template_name in self._fragment_cache:
            return self._fragment_cache[template_name]

        # Try to discover fragments for this template
        await self._analyze_fragment(template_name)
        return self._fragment_cache.get(template_name, [])

    async def get_autocomplete_suggestions(
        self, context: str, cursor_position: int = 0, template_name: str = "unknown"
    ) -> list[AutocompleteItem]:
        """Get autocomplete suggestions for the given context."""
        cache_key = "global"
        if cache_key not in self._autocomplete_cache:
            await self._build_autocomplete_index()

        all_items = self._autocomplete_cache[cache_key]

        # Extract the current word being typed
        before_cursor = context[:cursor_position]
        current_word = self._extract_current_word(before_cursor)

        if not current_word:
            return all_items[:20]  # Return top 20 suggestions

        # Filter suggestions based on current word
        filtered = [
            item for item in all_items if current_word.lower() in item.name.lower()
        ]

        # Sort by relevance (exact matches first, then starts with, then contains)
        filtered.sort(
            key=lambda x: (
                not x.name.lower().startswith(current_word.lower()),
                not x.name.lower() == current_word.lower(),
                x.name.lower(),
            )
        )

        return filtered[:10]  # Return top 10 matches

    @staticmethod
    def _extract_current_word(text: str) -> str:
        """Extract the current word being typed from template context."""
        # Look for word characters at the end of the text
        match = re.search(
            r"[\w.]+$", text
        )  # REGEX OK: extract word at cursor for autocomplete
        return match.group(0) if match else ""

    async def render_fragment(
        self,
        fragment_name: str,
        context: dict[str, t.Any] | None = None,
        template_name: str | None = None,
        secure: bool = False,
    ) -> str:
        """Render a specific template fragment."""
        if not self.base_templates:
            raise RuntimeError("Templates not initialized")

        # Find the fragment
        fragment_info = await self._find_fragment(fragment_name, template_name)
        if not fragment_info:
            raise TemplateNotFound(f"Fragment '{fragment_name}' not found")

        env = self._get_template_environment(secure=secure)

        try:
            if fragment_info.block_name:
                # Render specific block
                template = env.get_template(fragment_info.template_path)
                # render_block exists in Jinja2 runtime but not in type stubs
                return str(
                    template.render_block(  # type: ignore[attr-defined]
                        fragment_info.block_name, context or {}
                    )
                )
            else:
                # Render entire template
                template = env.get_template(fragment_info.template_path)
                return str(template.render(context or {}))

        except Exception as e:
            raise TemplateError(f"Error rendering fragment '{fragment_name}': {e}")

    async def _find_fragment(
        self, fragment_name: str, template_name: str | None = None
    ) -> FragmentInfo | None:
        """Find fragment by name, optionally within a specific template."""
        # Search in specific template first
        if template_name and template_name in self._fragment_cache:
            for fragment in self._fragment_cache[template_name]:
                if fragment.name == fragment_name:
                    return fragment

        # Search across all fragments
        for fragments in self._fragment_cache.values():
            for fragment in fragments:
                if fragment.name == fragment_name:
                    return fragment

        return None

    async def precompile_templates(self) -> dict[str, Template]:
        """Precompile templates for performance optimization."""
        if not self.settings.precompile_templates:
            return {}

        env = self._get_template_environment()
        if not env.loader:
            return {}

        compiled_templates = {}

        with suppress(Exception):
            template_names = await asyncio.get_event_loop().run_in_executor(
                None, env.loader.list_templates
            )

            for template_name in template_names:
                with suppress(Exception):
                    template = env.get_template(template_name)
                    compiled_templates[template_name] = template

        return compiled_templates

    async def get_template_dependencies(self, template_name: str) -> set[str]:
        """Get dependencies for a template (extends, includes, imports)."""
        if template_name in self._template_dependencies:
            return self._template_dependencies[template_name]

        dependencies = set()
        env = self._get_template_environment()

        with suppress(Exception):
            source, _, _ = env.loader.get_source(env, template_name)  # type: ignore[union-attr,misc]
            parsed = env.parse(source, template_name)

            # Find extends, includes, and imports
            node: t.Any
            # find_all accepts strings but type stubs expect Node types
            for node in parsed.find_all(
                t.cast(t.Any, ("Extends", "Include", "FromImport"))
            ):
                if hasattr(node, "template") and hasattr(node.template, "value"):
                    dependencies.add(node.template.value)

            self._template_dependencies[template_name] = dependencies

        return dependencies

    def clear_caches(self) -> None:
        """Clear all internal caches."""
        self._validation_cache.clear()
        self._fragment_cache.clear()
        self._autocomplete_cache.clear()
        self._template_dependencies.clear()


MODULE_ID = UUID("01937d87-1234-7890-abcd-1234567890ab")
MODULE_STATUS = AdapterStatus.EXPERIMENTAL

# Register the advanced manager
with suppress(Exception):
    depends.set("hybrid_template_manager", HybridTemplatesManager)
