"""FastBlocks syntax support and autocomplete system."""

import re
from contextlib import suppress
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any
from uuid import UUID

from acb.config import Settings
from acb.depends import depends


@dataclass
class CompletionItem:
    """Auto-completion item for FastBlocks syntax."""

    label: str
    kind: str  # 'function', 'variable', 'filter', 'block', 'component'
    detail: str = ""
    documentation: str = ""
    insert_text: str = ""
    parameters: list[str] = field(default_factory=list)
    category: str = "general"
    priority: int = 0


@dataclass
class SyntaxError:
    """FastBlocks syntax error."""

    line: int
    column: int
    message: str
    severity: str = "error"  # 'error', 'warning', 'info'
    code: str = ""
    fix_suggestion: str = ""


class FastBlocksSyntaxSettings(Settings):
    """Settings for FastBlocks syntax support."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d87-1234-5678-9abc-123456789def")
    MODULE_STATUS: str = "stable"

    # Completion settings
    max_completions: int = 50
    completion_timeout: float = 1.0
    enable_snippets: bool = True
    enable_parameter_hints: bool = True

    # Syntax highlighting
    enable_highlighting: bool = True
    highlight_delimiters: bool = True
    highlight_filters: bool = True
    highlight_functions: bool = True

    # Error checking
    enable_error_checking: bool = True
    check_template_syntax: bool = True
    check_filter_existence: bool = True
    check_function_calls: bool = True

    # Template delimiters
    variable_start: str = "[["
    variable_end: str = "]]"
    block_start: str = "[%"
    block_end: str = "%]"
    comment_start: str = "[#"
    comment_end: str = "#]"


class FastBlocksSyntaxSupport:
    """FastBlocks syntax support and autocomplete provider."""

    # Required ACB 0.19.0+ metadata
    MODULE_ID: UUID = UUID("01937d87-1234-5678-9abc-123456789def")
    MODULE_STATUS: str = "stable"

    def __init__(self) -> None:
        """Initialize syntax support."""
        self.settings: FastBlocksSyntaxSettings | None = None
        self._completions_cache: dict[str, list[CompletionItem]] = {}
        self._syntax_patterns: dict[str, re.Pattern[str]] = {}
        self._builtin_filters: set[str] = set()
        self._builtin_functions: set[str] = set()
        self._custom_components: set[str] = set()

        # Register with ACB
        with suppress(Exception):
            depends.set(self)

        self._initialize_patterns()
        self._load_builtin_definitions()

    def _initialize_patterns(self) -> None:
        """Initialize regex patterns for syntax parsing."""
        if not self.settings:
            self.settings = FastBlocksSyntaxSettings()

        # Escape delimiters for regex
        var_start = re.escape(self.settings.variable_start)
        var_end = re.escape(self.settings.variable_end)
        block_start = re.escape(self.settings.block_start)
        block_end = re.escape(self.settings.block_end)
        comment_start = re.escape(self.settings.comment_start)
        comment_end = re.escape(self.settings.comment_end)

        self._syntax_patterns = {
            "variable": re.compile(
                rf"{var_start}\s*([^{var_end}]*?)\s*{var_end}"
            ),  # REGEX OK: template variable syntax
            "block": re.compile(
                rf"{block_start}\s*([^{block_end}]*?)\s*{block_end}"
            ),  # REGEX OK: template block syntax
            "comment": re.compile(  # REGEX OK: template comment syntax
                rf"{comment_start}\s*([^{comment_end}]*?)\s*{comment_end}"
            ),
            "filter": re.compile(
                r"\|\s*(\w+)(?:\([^)]*\))?"
            ),  # REGEX OK: template filter syntax
            "function": re.compile(r"(\w+)\s*\("),  # REGEX OK: template function calls
            "component": re.compile(
                r"render_component\s*\(\s*[\"']([^\"']+)[\"']"
            ),  # REGEX OK: component rendering syntax
            "string": re.compile(
                r'["\']([^"\']*)["\']'
            ),  # REGEX OK: string literals in templates
            "identifier": re.compile(r"\b(\w+)\b"),  # REGEX OK: variable identifiers
        }

    def _load_builtin_definitions(self) -> None:
        """Load built-in Jinja2 filters and functions."""
        self._builtin_filters = {
            # Jinja2 built-in filters
            "abs",
            "attr",
            "batch",
            "capitalize",
            "center",
            "default",
            "dictsort",
            "escape",
            "filesizeformat",
            "first",
            "float",
            "forceescape",
            "format",
            "groupby",
            "indent",
            "int",
            "join",
            "last",
            "length",
            "list",
            "lower",
            "map",
            "max",
            "min",
            "pprint",
            "random",
            "reject",
            "rejectattr",
            "replace",
            "reverse",
            "round",
            "safe",
            "select",
            "selectattr",
            "slice",
            "sort",
            "string",
            "striptags",
            "sum",
            "title",
            "tojson",
            "trim",
            "truncate",
            "unique",
            "upper",
            "urlencode",
            "urlize",
            "wordcount",
            "wordwrap",
            "xmlattr",
            # FastBlocks custom filters
            "img",
            "icon",
            "stylesheet",
            "component_class",
            "duotone",
            "interactive",
            "button_icon",
            "ph_icon",
            "ph_class",
            "hero_icon",
            "remix_icon",
            "material_icon",
            "webawesome_class",
            "kelp_class",
            "cloudflare_img",
            "twicpics_img",
        }

        self._builtin_functions = {
            # Jinja2 built-in functions
            "range",
            "lipsum",
            "dict",
            "cycler",
            "joiner",
            "namespace",
            # FastBlocks custom functions
            "render_component",
            "get_adapter",
            "include_template",
            "extend_template",
            "load_static",
            "url_for",
            "csrf_token",
            "flash_messages",
            "get_config",
            "phosphor_stylesheet_links",
            "ph_duotone",
            "ph_interactive",
            "ph_button_icon",
            "heroicons_stylesheet_links",
            "remixicon_stylesheet_links",
            "material_icons_links",
            "webawesome_stylesheet_links",
            "kelp_stylesheet_links",
        }

    def get_completions(
        self, content: str, line: int, column: int, context: str = ""
    ) -> list[CompletionItem]:
        """Get auto-completion suggestions for given position."""
        if not self.settings:
            self.settings = FastBlocksSyntaxSettings()

        # Find current context
        current_line = (
            content.split("\n")[line] if line < len(content.split("\n")) else ""
        )
        prefix = current_line[:column]

        completions: list[CompletionItem] = []

        # Determine completion context
        if self._is_in_variable_context(prefix):
            completions.extend(self._get_variable_completions(prefix))
        elif self._is_in_block_context(prefix):
            completions.extend(self._get_block_completions(prefix))
        elif self._is_in_filter_context(prefix):
            completions.extend(self._get_filter_completions(prefix))
        elif self._is_in_function_context(prefix):
            completions.extend(self._get_function_completions(prefix))
        else:
            # General completions
            completions.extend(self._get_general_completions(prefix))

        # Sort by priority and limit results
        completions.sort(key=lambda x: (-x.priority, x.label))
        return completions[: self.settings.max_completions]

    def _is_in_variable_context(self, prefix: str) -> bool:
        """Check if cursor is in variable context."""
        if not self.settings:
            return False
        return (
            self.settings.variable_start in prefix
            and self.settings.variable_end
            not in prefix.split(self.settings.variable_start)[-1]
        )

    def _is_in_block_context(self, prefix: str) -> bool:
        """Check if cursor is in block context."""
        if not self.settings:
            return False
        return (
            self.settings.block_start in prefix
            and self.settings.block_end
            not in prefix.split(self.settings.block_start)[-1]
        )

    def _is_in_filter_context(self, prefix: str) -> bool:
        """Check if cursor is after a pipe for filter completion."""
        return "|" in prefix and not prefix.rstrip().endswith("|")

    def _is_in_function_context(self, prefix: str) -> bool:
        """Check if cursor is in function call context."""
        return "(" in prefix and ")" not in prefix.split("(")[-1]

    def _get_variable_completions(self, prefix: str) -> list[CompletionItem]:
        """Get completions for variable context."""
        return [
            CompletionItem(
                label="request",
                kind="variable",
                detail="Current request object",
                documentation="The current HTTP request with all headers and data",
                priority=10,
            ),
            CompletionItem(
                label="user",
                kind="variable",
                detail="Current user object",
                documentation="The authenticated user (if available)",
                priority=9,
            ),
            CompletionItem(
                label="config",
                kind="variable",
                detail="Application configuration",
                documentation="FastBlocks configuration settings",
                priority=8,
            ),
            CompletionItem(
                label="now",
                kind="variable",
                detail="Current datetime",
                documentation="Current datetime object",
                priority=7,
            ),
        ]

    def _get_block_completions(self, prefix: str) -> list[CompletionItem]:
        """Get completions for block context."""
        return [
            CompletionItem(
                label="if",
                kind="block",
                detail="Conditional block",
                insert_text="if condition %]\n    content\n[% endif",
                documentation="Conditional rendering block",
                priority=10,
            ),
            CompletionItem(
                label="for",
                kind="block",
                detail="Loop block",
                insert_text="for item in items %]\n    [[ item ]]\n[% endfor",
                documentation="Iteration loop block",
                priority=10,
            ),
            CompletionItem(
                label="block",
                kind="block",
                detail="Template inheritance block",
                insert_text="block name %]\n    content\n[% endblock",
                documentation="Template inheritance block",
                priority=9,
            ),
            CompletionItem(
                label="extends",
                kind="block",
                detail="Template inheritance",
                insert_text='extends "base.html"',
                documentation="Extend a parent template",
                priority=9,
            ),
            CompletionItem(
                label="include",
                kind="block",
                detail="Include template",
                insert_text='include "partial.html"',
                documentation="Include another template",
                priority=8,
            ),
            CompletionItem(
                label="set",
                kind="block",
                detail="Variable assignment",
                insert_text="set variable = value",
                documentation="Set a template variable",
                priority=8,
            ),
        ]

    def _get_filter_completions(self, prefix: str) -> list[CompletionItem]:
        """Get completions for filter context."""
        completions = []

        for filter_name in sorted(self._builtin_filters):
            documentation = self._get_filter_documentation(filter_name)
            completions.append(
                CompletionItem(
                    label=filter_name,
                    kind="filter",
                    detail=f"Filter: {filter_name}",
                    documentation=documentation,
                    priority=8 if filter_name.startswith(("ph_", "img", "icon")) else 5,
                )
            )

        return completions

    def _get_function_completions(self, prefix: str) -> list[CompletionItem]:
        """Get completions for function context."""
        completions = []

        for func_name in sorted(self._builtin_functions):
            documentation = self._get_function_documentation(func_name)
            parameters = self._get_function_parameters(func_name)

            completions.append(
                CompletionItem(
                    label=func_name,
                    kind="function",
                    detail=f"Function: {func_name}",
                    documentation=documentation,
                    parameters=parameters,
                    priority=8 if func_name.startswith("render_") else 5,
                )
            )

        return completions

    def _get_general_completions(self, prefix: str) -> list[CompletionItem]:
        """Get general completions."""
        if not self.settings:
            self.settings = FastBlocksSyntaxSettings()

        return [
            CompletionItem(
                label=f"{self.settings.variable_start}  {self.settings.variable_end}",
                kind="snippet",
                detail="Variable output",
                insert_text=f"{self.settings.variable_start} variable {self.settings.variable_end}",
                documentation="Output a variable value",
                priority=10,
            ),
            CompletionItem(
                label=f"{self.settings.block_start}  {self.settings.block_end}",
                kind="snippet",
                detail="Block statement",
                insert_text=f"{self.settings.block_start} block {self.settings.block_end}",
                documentation="Template logic block",
                priority=10,
            ),
            CompletionItem(
                label=f"{self.settings.comment_start}  {self.settings.comment_end}",
                kind="snippet",
                detail="Comment",
                insert_text=f"{self.settings.comment_start} comment {self.settings.comment_end}",
                documentation="Template comment",
                priority=5,
            ),
        ]

    def _get_filter_documentation(self, filter_name: str) -> str:
        """Get documentation for a filter."""
        docs = {
            "img": "Generate image tag with adapter support",
            "icon": "Generate icon tag with variant support",
            "ph_icon": "Generate Phosphor icon with customization",
            "ph_class": "Get Phosphor icon CSS class",
            "hero_icon": "Generate Heroicons icon",
            "remix_icon": "Generate Remix icon",
            "material_icon": "Generate Material Design icon",
            "cloudflare_img": "Cloudflare Images optimization",
            "twicpics_img": "TwicPics image transformation",
            "default": "Provide default value if variable is undefined",
            "length": "Get length of sequence or mapping",
            "upper": "Convert string to uppercase",
            "lower": "Convert string to lowercase",
            "title": "Convert string to title case",
            "capitalize": "Capitalize first letter",
            "truncate": "Truncate string to specified length",
            "join": "Join sequence elements with separator",
            "replace": "Replace substring with another string",
            "safe": "Mark string as safe HTML",
            "escape": "Escape HTML characters",
            "tojson": "Convert value to JSON string",
        }
        return docs.get(filter_name, f"Jinja2 {filter_name} filter")

    def _get_function_documentation(self, func_name: str) -> str:
        """Get documentation for a function."""
        docs = {
            "render_component": "Render HTMY component with context",
            "get_adapter": "Get adapter instance by name",
            "include_template": "Include template with context",
            "url_for": "Generate URL for route",
            "csrf_token": "Generate CSRF token",
            "flash_messages": "Get flash messages",
            "get_config": "Get configuration value",
            "ph_duotone": "Generate duotone Phosphor icon",
            "ph_interactive": "Generate interactive Phosphor icon",
            "ph_button_icon": "Generate button with Phosphor icon",
            "range": "Generate range of numbers",
            "dict": "Create dictionary from arguments",
            "lipsum": "Generate Lorem Ipsum text",
        }
        return docs.get(func_name, f"Jinja2 {func_name} function")

    def _get_function_parameters(self, func_name: str) -> list[str]:
        """Get function parameters."""
        params = {
            "render_component": ["component_name", "context={}"],
            "get_adapter": ["adapter_name"],
            "include_template": ["template_name", "**context"],
            "url_for": ["route_name", "**params"],
            "ph_duotone": ["icon_name", "primary_color=None", "secondary_color=None"],
            "ph_interactive": ["icon_name", "variant='regular'", "action=None"],
            "ph_button_icon": ["icon_name", "text=None", "variant='regular'"],
            "range": ["start", "stop=None", "step=1"],
            "dict": ["**items"],
        }
        return params.get(func_name, [])

    def check_syntax(
        self, content: str, template_path: Path | None = None
    ) -> list[SyntaxError]:
        """Check template syntax and return errors."""
        if not self.settings or not self.settings.enable_error_checking:
            return []

        errors: list[SyntaxError] = []
        lines = content.split("\n")

        for line_num, line in enumerate(lines):
            # Check delimiter balance
            errors.extend(self._check_delimiter_balance(line, line_num))

            # Check filter existence
            if self.settings.check_filter_existence:
                errors.extend(self._check_filter_existence(line, line_num))

            # Check function calls
            if self.settings.check_function_calls:
                errors.extend(self._check_function_calls(line, line_num))

        return errors

    def _check_delimiter_balance(self, line: str, line_num: int) -> list[SyntaxError]:
        """Check if delimiters are balanced."""
        if not self.settings:
            return []

        errors = []

        # Check variable delimiters
        var_opens = line.count(self.settings.variable_start)
        var_closes = line.count(self.settings.variable_end)
        if var_opens != var_closes:
            errors.append(
                SyntaxError(
                    line=line_num,
                    column=0,
                    message=f"Unbalanced variable delimiters: {var_opens} opens, {var_closes} closes",
                    severity="error",
                    code="unbalanced_delimiters",
                    fix_suggestion=f"Add missing {self.settings.variable_end if var_opens > var_closes else self.settings.variable_start}",
                )
            )

        # Check block delimiters
        block_opens = line.count(self.settings.block_start)
        block_closes = line.count(self.settings.block_end)
        if block_opens != block_closes:
            errors.append(
                SyntaxError(
                    line=line_num,
                    column=0,
                    message=f"Unbalanced block delimiters: {block_opens} opens, {block_closes} closes",
                    severity="error",
                    code="unbalanced_delimiters",
                    fix_suggestion=f"Add missing {self.settings.block_end if block_opens > block_closes else self.settings.block_start}",
                )
            )

        return errors

    def _check_filter_existence(self, line: str, line_num: int) -> list[SyntaxError]:
        """Check if filters exist."""
        errors = []

        if "filter" in self._syntax_patterns:
            for match in self._syntax_patterns["filter"].finditer(line):
                filter_name = match.group(1)
                if filter_name not in self._builtin_filters:
                    errors.append(
                        SyntaxError(
                            line=line_num,
                            column=match.start(),
                            message=f"Unknown filter: {filter_name}",
                            severity="warning",
                            code="unknown_filter",
                            fix_suggestion="Check filter name or register custom filter",
                        )
                    )

        return errors

    def _check_function_calls(self, line: str, line_num: int) -> list[SyntaxError]:
        """Check function calls."""
        errors = []

        if "function" in self._syntax_patterns:
            for match in self._syntax_patterns["function"].finditer(line):
                func_name = match.group(1)
                if (
                    func_name not in self._builtin_functions
                    and not func_name.startswith("_")
                ):
                    errors.append(
                        SyntaxError(
                            line=line_num,
                            column=match.start(),
                            message=f"Unknown function: {func_name}",
                            severity="warning",
                            code="unknown_function",
                            fix_suggestion="Check function name or import if custom",
                        )
                    )

        return errors

    def get_hover_info(self, content: str, line: int, column: int) -> str | None:
        """Get hover information for symbol at position."""
        lines = content.split("\n")
        if line >= len(lines):
            return None

        current_line = lines[line]

        # Find word at position
        word_start = column
        word_end = column

        while word_start > 0 and current_line[word_start - 1].isalnum():
            word_start -= 1

        while word_end < len(current_line) and current_line[word_end].isalnum():
            word_end += 1

        word = current_line[word_start:word_end]

        if word in self._builtin_filters:
            return f"**Filter: {word}**\n\n{self._get_filter_documentation(word)}"
        elif word in self._builtin_functions:
            params = self._get_function_parameters(word)
            param_str = ", ".join(params) if params else ""
            return f"**Function: {word}({param_str})**\n\n{self._get_function_documentation(word)}"

        return None

    def format_template(self, content: str) -> str:
        """Format template content."""
        # Simple formatting - in a real implementation this would be more sophisticated
        lines = content.split("\n")
        formatted_lines = []
        indent_level = 0

        for line in lines:
            stripped = line.strip()

            # Decrease indent for end blocks
            if stripped.startswith(("[% end", "[% else")):
                indent_level = max(0, indent_level - 1)

            # Add formatted line
            if stripped:
                formatted_lines.append("    " * indent_level + stripped)
            else:
                formatted_lines.append("")

            # Increase indent for start blocks
            if any(
                stripped.startswith(f"[% {block}")
                for block in ("if", "for", "block", "macro")
            ):
                indent_level += 1
            elif stripped.startswith("[% else"):
                indent_level += 1

        return "\n".join(formatted_lines)


# Template filter registration for FastBlocks
def register_syntax_filters(env: Any) -> None:
    """Register syntax support filters for Jinja2 templates."""

    @env.filter("format_template")  # type: ignore[misc]
    def format_template_filter(content: str) -> str:
        """Template filter for formatting FastBlocks templates."""
        syntax_support = depends.get_sync("syntax_support")
        if isinstance(syntax_support, FastBlocksSyntaxSupport):
            return syntax_support.format_template(content)
        return content

    @env.global_("syntax_check")  # type: ignore[misc]
    def syntax_check_global(content: str) -> list[dict[str, Any]]:
        """Global function for syntax checking."""
        syntax_support = depends.get_sync("syntax_support")
        if isinstance(syntax_support, FastBlocksSyntaxSupport):
            errors = syntax_support.check_syntax(content)
            return [
                {
                    "line": error.line,
                    "column": error.column,
                    "message": error.message,
                    "severity": error.severity,
                    "code": error.code,
                    "fix": error.fix_suggestion,
                }
                for error in errors
            ]
        return []


# ACB 0.19.0+ compatibility
__all__ = [
    "FastBlocksSyntaxSupport",
    "FastBlocksSyntaxSettings",
    "CompletionItem",
    "SyntaxError",
    "register_syntax_filters",
]
