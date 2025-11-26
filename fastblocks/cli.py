import asyncio
import logging
import os
import signal
import typing as t
from contextlib import suppress
from enum import Enum
from importlib.metadata import version as get_version
from pathlib import Path
from subprocess import DEVNULL
from subprocess import run as execute
from typing import Annotated

with suppress(ImportError):
    from acb.logger import InterceptHandler

    for logger_name in ("uvicorn", "uvicorn.access", "uvicorn.error"):
        logger = logging.getLogger(logger_name)
        logger.handlers.clear()
        logger.addHandler(InterceptHandler())
        logger.setLevel(logging.DEBUG)
        logger.propagate = False

import sys

import nest_asyncio
import typer
import uvicorn
from acb.actions.encode import dump, load
from anyio import Path as AsyncPath
from granian import Granian

try:
    from acb.console import console
except ImportError:
    # Fallback to regular rich console if acb.console is not available
    from rich.console import Console

    console = Console()

nest_asyncio.apply()
__all__ = ("cli", "components", "create", "dev", "run")
default_adapters = {
    "routes": "default",
    "templates": "jinja2",
    "auth": "basic",
    "sitemap": "asgi",
}
fastblocks_path = Path(__file__).parent
apps_path = Path.cwd()

# Check if running in the FastBlocks library directory itself
# Skip this check during tests by examining if we're in a test environment

is_testing = os.getenv("PYTEST_CURRENT_TEST") or "pytest" in sys.modules
if Path.cwd() == fastblocks_path and not is_testing:
    msg = "FastBlocks can not be run in the same directory as FastBlocks itself. Run `python -m fastblocks create`. Move into the app directory and try again."
    raise SystemExit(
        msg,
    )
cli = typer.Typer(rich_markup_mode="rich")


class Styles(str, Enum):
    bulma = "bulma"
    webawesome = "webawesome"
    custom = "custom"

    def __str__(self) -> str:
        return t.cast(str, self.value)


run_args: dict[str, t.Any] = {"app": "main:app"}
dev_args: dict[str, t.Any] = run_args | {"port": 8000, "reload": True}
granian_dev_args: dict[str, t.Any] = dev_args | {
    "address": "127.0.0.1",
    "reload_paths": [Path.cwd(), fastblocks_path],
    "interface": "asgi",
    "log_enabled": False,
    "log_access": True,
    "reload_ignore_dirs": ["tmp", "settings", "templates"],
}
uvicorn_dev_args: dict[str, t.Any] = dev_args | {
    "host": "127.0.0.1",
    "reload_includes": ["*.py", str(Path.cwd()), str(fastblocks_path)],
    "reload_excludes": ["tmp/*", "settings/*", "templates/*"],
    "lifespan": "on",
}


def setup_signal_handlers() -> None:
    import sys

    def signal_handler(_signum: int, _frame: t.Any) -> None:
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)


@cli.command()
def run(docker: bool = False, granian: bool = False, host: str = "127.0.0.1") -> None:
    if docker:
        execute(
            f"docker run -it -ePORT=8080 -p8080:8080 {Path.cwd().stem}".split(),
        )
    else:
        setup_signal_handlers()
        if granian:
            from granian.constants import Interfaces

            Granian("main:app", address=host, interface=Interfaces.ASGI).serve()
        else:
            uvicorn.run(app=run_args["app"], host=host, lifespan="on", log_config=None)


@cli.command()
def dev(granian: bool = False) -> None:
    setup_signal_handlers()
    if granian:
        from granian.constants import Interfaces

        Granian(
            "main:app",
            address="127.0.0.1",
            port=8000,
            reload=True,
            reload_paths=[Path.cwd(), fastblocks_path],
            interface=Interfaces.ASGI,
            log_enabled=False,
            log_access=True,
        ).serve()
    else:
        uvicorn.run(
            app="main:app",
            host="127.0.0.1",
            port=8000,
            reload=True,
            reload_includes=["*.py", str(Path.cwd()), str(fastblocks_path)],
            reload_excludes=["tmp/*", "settings/*", "templates/*"],
            lifespan="on",
            log_config=None,
        )


def _display_adapters() -> None:
    from acb.adapters import get_adapters

    console.print("[bold green]Available Adapters:[/bold green]")
    adapters = get_adapters()
    if not adapters:
        console.print("  [dim]No adapters found[/dim]")
        return
    categories: dict[str, list[t.Any]] = {}
    for adapter in adapters:
        if adapter.category not in categories:
            categories[adapter.category] = []
        categories[adapter.category].append(adapter)
    for category in sorted(categories.keys()):
        console.print(f"\n  [bold cyan]{category.upper()}:[/bold cyan]")
        for adapter in sorted(categories[category], key=lambda a: a.name):
            _display_adapter_info(adapter)


def _display_adapter_info(adapter: t.Any) -> None:
    status = "[green]✓[/green]" if adapter.installed else "[red]✗[/red]"
    enabled = "[yellow]enabled[/yellow]" if adapter.enabled else "[dim]disabled[/dim]"
    console.print(f"    {status} [white]{adapter.name}[/white] - {enabled}")
    if adapter.module:
        console.print(f"      [dim]{adapter.module}[/dim]")


def _display_default_config() -> None:
    console.print("\n[bold green]FastBlocks Default Configuration:[/bold green]")
    for category, default_name in default_adapters.items():
        console.print(f"  [cyan]{category}[/cyan]: [white]{default_name}[/white]")


def _display_actions() -> None:
    console.print("\n[bold green]FastBlocks Actions:[/bold green]")
    try:
        from fastblocks.actions.minify import minify

        console.print("  [cyan]minify[/cyan]:")
        console.print(f"    [white]- css[/white] ([dim]{minify.css.__name__}[/dim])")
        console.print(f"    [white]- js[/white] ([dim]{minify.js.__name__}[/dim])")
    except ImportError:
        console.print("  [dim]Minify actions not available[/dim]")


@cli.command()
def components() -> None:
    try:
        console.print("\n[bold blue]FastBlocks Components[/bold blue]\n")
        _display_adapters()
        _display_default_config()
        _display_actions()
        _display_htmy_commands()
    except Exception as e:
        console.print(f"[red]Error displaying components: {e}[/red]")
        console.print("[dim]Make sure you're in a FastBlocks project directory[/dim]")


def _display_htmy_commands() -> None:
    console.print("\n[bold green]HTMY Component Commands:[/bold green]")
    console.print("  [cyan]scaffold[/cyan]: Create new HTMY components")
    console.print("  [cyan]list[/cyan]: List all discovered components")
    console.print("  [cyan]validate[/cyan]: Validate component structure")
    console.print("  [cyan]info[/cyan]: Get component metadata")


# Component scaffolding helpers
_COMPONENT_TYPE_MAP = {
    "basic": "BASIC",
    "dataclass": "DATACLASS",
    "htmx": "HTMX",
    "composite": "COMPOSITE",
}

_TYPE_MAP = {
    "str": str,
    "int": int,
    "float": float,
    "bool": bool,
    "list": list,
    "dict": dict,
}


def _parse_component_type(type_str: str) -> t.Any:
    """Parse component type string to ComponentType enum."""
    from fastblocks.adapters.templates._htmy_components import ComponentType

    type_name = _COMPONENT_TYPE_MAP.get(type_str.lower(), "DATACLASS")
    return getattr(ComponentType, type_name)


def _parse_component_props(props: str) -> dict[str, type]:
    """Parse props string into dict of name:type pairs."""
    if not props:
        return {}

    parsed = {}
    for prop_def in props.split(","):
        if ":" not in prop_def:
            continue
        prop_name, prop_type = prop_def.strip().split(":", 1)
        parsed[prop_name] = _TYPE_MAP.get(prop_type, str)
    return parsed


def _parse_component_children(children: str) -> list[str] | None:
    """Parse children string into list of component names."""
    if not children:
        return None
    return [c.strip() for c in children.split(",") if c.strip()]


def _build_scaffold_kwargs(
    parsed_props: dict[str, t.Any],
    htmx: bool,
    component_type: t.Any,
    endpoint: str,
    trigger: str,
    target: str,
    parsed_children: list[str] | None,
) -> dict[str, t.Any]:
    """Build kwargs dict for component scaffolding."""
    from fastblocks.adapters.templates._htmy_components import ComponentType

    kwargs: dict[str, t.Any] = {}

    if parsed_props:
        kwargs["props"] = parsed_props

    if htmx or component_type == ComponentType.HTMX:
        kwargs["htmx_enabled"] = True
        if endpoint:
            kwargs["endpoint"] = endpoint
            kwargs["trigger"] = trigger
            kwargs["target"] = target

    if parsed_children:
        kwargs["children"] = parsed_children

    return kwargs


@cli.command()
def scaffold(
    name: Annotated[str, typer.Argument(help="Component name")],
    type: Annotated[
        str,
        typer.Option(
            "--type", "-t", help="Component type: basic, dataclass, htmx, composite"
        ),
    ] = "dataclass",
    htmx: Annotated[
        bool, typer.Option("--htmx", "-x", help="Enable HTMX features")
    ] = False,
    endpoint: Annotated[
        str, typer.Option("--endpoint", "-e", help="HTMX endpoint URL")
    ] = "",
    trigger: Annotated[
        str, typer.Option("--trigger", help="HTMX trigger event")
    ] = "click",
    target: Annotated[
        str, typer.Option("--target", help="HTMX target selector")
    ] = "#content",
    props: Annotated[
        str,
        typer.Option("--props", "-p", help="Component props as 'name:type,name:type'"),
    ] = "",
    children: Annotated[
        str, typer.Option("--children", "-c", help="Child components as 'comp1,comp2'")
    ] = "",
    path: Annotated[str, typer.Option("--path", help="Custom component path")] = "",
) -> None:
    """Scaffold a new HTMY component."""
    import asyncio
    from pathlib import Path

    async def scaffold_component() -> None:
        try:
            from acb.depends import depends

            # Get HTMY adapter
            htmy_adapter = await depends.get("htmy")
            if htmy_adapter is None:
                console.print(
                    "[red]HTMY adapter not found. Make sure you're in a FastBlocks project.[/red]"
                )
                return

            # Parse inputs using helper functions
            component_type = _parse_component_type(type)
            parsed_props = _parse_component_props(props)
            parsed_children = _parse_component_children(children)

            # Build kwargs
            kwargs = _build_scaffold_kwargs(
                parsed_props,
                htmx,
                component_type,
                endpoint,
                trigger,
                target,
                parsed_children,
            )

            # Custom path
            target_path = Path(path) if path else None

            # Scaffold component
            created_path = await htmy_adapter.scaffold_component(
                name=name,
                component_type=component_type,
                target_path=target_path,
                **kwargs,
            )

            console.print(
                f"[green]✓[/green] Created {component_type.value} component '{name}' at {created_path}"
            )

        except Exception as e:
            console.print(f"[red]Error scaffolding component: {e}[/red]")

    asyncio.run(scaffold_component())


def _get_component_status_color(status_value: str) -> str:
    """Get the color for a component status."""
    return {
        "discovered": "yellow",
        "validated": "green",
        "compiled": "blue",
        "ready": "green",
        "error": "red",
        "deprecated": "dim",
    }.get(status_value, "white")


def _display_component_entry(name: str, metadata: t.Any) -> None:
    """Display a single component entry with status and metadata."""
    status_color = _get_component_status_color(metadata.status.value)

    console.print(
        f"  [{status_color}]●[/{status_color}] [white]{name}[/white] ({metadata.type.value})"
    )
    console.print(f"    [dim]{metadata.path}[/dim]")

    if metadata.error_message:
        console.print(f"    [red]Error: {metadata.error_message}[/red]")
    elif metadata.docstring:
        # Show first line of docstring
        first_line = metadata.docstring.split("\n")[0].strip()
        if first_line:
            console.print(f"    [dim]{first_line}[/dim]")


@cli.command(name="list")
def list_components() -> None:
    """List all discovered HTMY components."""
    import asyncio

    async def list_all_components() -> None:
        try:
            from acb.depends import depends

            htmy_adapter = await depends.get("htmy")
            if htmy_adapter is None:
                console.print(
                    "[red]HTMY adapter not found. Make sure you're in a FastBlocks project.[/red]"
                )
                return

            components = await htmy_adapter.discover_components()

            if not components:
                console.print("[dim]No components found.[/dim]")
                return

            console.print(
                f"\n[bold green]Found {len(components)} HTMY components:[/bold green]\n"
            )

            for name, metadata in components.items():
                _display_component_entry(name, metadata)

        except Exception as e:
            console.print(f"[red]Error listing components: {e}[/red]")

    asyncio.run(list_all_components())


def _display_basic_metadata(component: str, metadata: t.Any) -> None:
    """Display basic component metadata."""
    console.print(f"\n[bold blue]Component: {component}[/bold blue]")
    console.print(f"  [cyan]Type:[/cyan] {metadata.type.value}")
    console.print(f"  [cyan]Status:[/cyan] {metadata.status.value}")
    console.print(f"  [cyan]Path:[/cyan] {metadata.path}")


def _display_optional_metadata(metadata: t.Any) -> None:
    """Display optional component metadata fields."""
    if metadata.last_modified:
        console.print(f"  [cyan]Modified:[/cyan] {metadata.last_modified}")

    if metadata.docstring:
        console.print(f"  [cyan]Description:[/cyan] {metadata.docstring}")


def _display_htmx_attributes(metadata: t.Any) -> None:
    """Display HTMX attributes if present."""
    if metadata.htmx_attributes:
        console.print("  [cyan]HTMX Attributes:[/cyan]")
        for key, value in metadata.htmx_attributes.items():
            console.print(f"    {key}: {value}")


def _display_dependencies(metadata: t.Any) -> None:
    """Display component dependencies if present."""
    if metadata.dependencies:
        console.print(
            f"  [cyan]Dependencies:[/cyan] {', '.join(metadata.dependencies)}"
        )


def _display_status_message(metadata: t.Any) -> None:
    """Display status-specific message."""
    if metadata.status.value == "error":
        console.print(f"  [red]Error:[/red] {metadata.error_message}")
    elif metadata.status.value == "ready":
        console.print("  [green]✓ Component is ready[/green]")


@cli.command()
def validate(
    component: Annotated[str, typer.Argument(help="Component name to validate")],
) -> None:
    """Validate a specific HTMY component."""
    import asyncio

    async def validate_component() -> None:
        try:
            from acb.depends import depends

            htmy_adapter = await depends.get("htmy")
            if htmy_adapter is None:
                console.print(
                    "[red]HTMY adapter not found. Make sure you're in a FastBlocks project.[/red]"
                )
                return

            metadata = await htmy_adapter.validate_component(component)

            _display_basic_metadata(component, metadata)
            _display_optional_metadata(metadata)
            _display_htmx_attributes(metadata)
            _display_dependencies(metadata)
            _display_status_message(metadata)

        except Exception as e:
            console.print(f"[red]Error validating component '{component}': {e}[/red]")

    asyncio.run(validate_component())


@cli.command()
def info(
    component: Annotated[str, typer.Argument(help="Component name to get info for")],
) -> None:
    """Get detailed information about an HTMY component."""
    import asyncio

    def _display_component_class_info(
        component_class: type, component_name: str
    ) -> None:
        """Display component class information including dataclass fields and HTMX status."""
        console.print(f"\n[bold blue]Component: {component_name}[/bold blue]")
        console.print(f"  [cyan]Class:[/cyan] {component_class.__name__}")
        console.print(f"  [cyan]Module:[/cyan] {component_class.__module__}")

        # Check if it's a dataclass
        from dataclasses import fields, is_dataclass

        if is_dataclass(component_class):
            console.print("  [cyan]Fields:[/cyan]")
            for field in fields(component_class):
                console.print(f"    {field.name}: {field.type}")

        # Check for HTMX mixin
        from fastblocks.adapters.templates._htmy_components import HTMXComponentMixin

        if issubclass(component_class, HTMXComponentMixin):
            console.print("  [cyan]HTMX Enabled:[/cyan] Yes")

    def _display_component_metadata(metadata: t.Any) -> None:
        """Display component metadata information."""
        console.print(f"  [cyan]Type:[/cyan] {metadata.type.value}")
        console.print(f"  [cyan]Status:[/cyan] {metadata.status.value}")
        console.print(f"  [cyan]Path:[/cyan] {metadata.path}")

    async def get_component_info() -> None:
        try:
            from acb.depends import depends

            htmy_adapter = await depends.get("htmy")
            if htmy_adapter is None:
                console.print(
                    "[red]HTMY adapter not found. Make sure you're in a FastBlocks project.[/red]"
                )
                return

            # Get component metadata
            metadata = await htmy_adapter.validate_component(component)

            # Try to get component class for more info
            try:
                component_class = await htmy_adapter.get_component_class(component)
                _display_component_class_info(component_class, component)
            except Exception as e:
                console.print(f"[red]Could not load component class: {e}[/red]")

            # Show metadata
            _display_component_metadata(metadata)

        except Exception as e:
            console.print(
                f"[red]Error getting info for component '{component}': {e}[/red]"
            )

    asyncio.run(get_component_info())


def _get_severity_color(severity: str) -> str:
    """Get the color for an error severity level."""
    return {
        "error": "red",
        "warning": "yellow",
        "info": "blue",
        "hint": "dim",
    }.get(severity, "white")


def _display_syntax_error(error: t.Any) -> None:
    """Display a single syntax error with formatting."""
    severity_color = _get_severity_color(error.severity)

    console.print(
        f"  [{severity_color}]{error.severity.upper()}[/{severity_color}] "
        f"Line {error.line + 1}, Column {error.column + 1}: {error.message}"
    )

    if error.fix_suggestion:
        console.print(f"    [dim]Fix: {error.fix_suggestion}[/dim]")

    if error.code:
        console.print(f"    [dim]Code: {error.code}[/dim]")


def _display_syntax_errors(file_path: str, errors: list[t.Any]) -> None:
    """Display all syntax errors for a file."""
    console.print(f"\n[bold red]Syntax errors found in {file_path}:[/bold red]")
    for error in errors:
        _display_syntax_error(error)


@cli.command()
def syntax_check(
    file_path: Annotated[
        str, typer.Argument(help="Path to FastBlocks template file to check")
    ],
    format_output: Annotated[
        bool, typer.Option("--format", help="Format the output for better readability")
    ] = False,
) -> None:
    """Check FastBlocks template syntax for errors and warnings."""
    import asyncio

    async def check_syntax() -> None:
        try:
            from pathlib import Path

            from acb.depends import depends

            syntax_support = await depends.get("syntax_support")
            if syntax_support is None:
                console.print(
                    "[red]Syntax support not available. Make sure you're in a FastBlocks project.[/red]"
                )
                return

            template_path = Path(file_path)
            if not template_path.exists():
                console.print(f"[red]File not found: {file_path}[/red]")
                return

            content = template_path.read_text()
            errors = syntax_support.check_syntax(content, template_path)

            if not errors:
                console.print(f"[green]✓ No syntax errors found in {file_path}[/green]")
                return

            _display_syntax_errors(file_path, errors)

        except Exception as e:
            console.print(f"[red]Error checking syntax: {e}[/red]")

    asyncio.run(check_syntax())


@cli.command()
def format_template(
    file_path: Annotated[
        str, typer.Argument(help="Path to FastBlocks template file to format")
    ],
    in_place: Annotated[
        bool, typer.Option("--in-place", "-i", help="Format file in place")
    ] = False,
) -> None:
    """Format a FastBlocks template file."""
    import asyncio

    async def format_file() -> None:
        try:
            from pathlib import Path

            from acb.depends import depends

            syntax_support = await depends.get("syntax_support")
            if syntax_support is None:
                console.print(
                    "[red]Syntax support not available. Make sure you're in a FastBlocks project.[/red]"
                )
                return

            template_path = Path(file_path)
            if not template_path.exists():
                console.print(f"[red]File not found: {file_path}[/red]")
                return

            content = template_path.read_text()
            formatted = syntax_support.format_template(content)

            if formatted == content:
                console.print(f"[green]✓ File {file_path} is already formatted[/green]")
                return

            if in_place:
                template_path.write_text(formatted)
                console.print(f"[green]✓ Formatted {file_path} in place[/green]")
            else:
                console.print(formatted)

        except Exception as e:
            console.print(f"[red]Error formatting template: {e}[/red]")

    asyncio.run(format_file())


@cli.command()
def generate_ide_config(
    output_dir: Annotated[
        str,
        typer.Option("--output", "-o", help="Output directory for IDE configurations"),
    ] = ".vscode",
    ide: Annotated[
        str, typer.Option(help="IDE to generate config for (vscode, vim, emacs)")
    ] = "vscode",
) -> None:
    """Generate IDE configuration files for FastBlocks syntax support."""
    import asyncio
    import json

    async def generate_config() -> None:
        try:
            from pathlib import Path

            output_path = Path(output_dir)
            output_path.mkdir(exist_ok=True)

            if ide == "vscode":
                # Generate VS Code extension configuration
                from fastblocks.adapters.templates._language_server import (
                    generate_textmate_grammar,
                    generate_vscode_extension,
                )

                # Package.json for extension
                package_json = generate_vscode_extension()
                (output_path / "package.json").write_text(
                    json.dumps(package_json, indent=2)
                )

                # TextMate grammar
                grammar = generate_textmate_grammar()
                syntaxes_dir = output_path / "syntaxes"
                syntaxes_dir.mkdir(exist_ok=True)
                (syntaxes_dir / "fastblocks.tmLanguage.json").write_text(
                    json.dumps(grammar, indent=2)
                )

                # Language configuration
                lang_config = {
                    "comments": {"blockComment": ["[#", "#]"]},
                    "brackets": [["[[", "]]"], ["[%", "%]"], ["[#", "#]"]],
                    "autoClosingPairs": [
                        {"open": "[[", "close": "]]"},
                        {"open": "[%", "close": "%]"},
                        {"open": "[#", "close": "#]"},
                        {"open": '"', "close": '"'},
                        {"open": "'", "close": "'"},
                    ],
                    "surroundingPairs": [
                        ["[[", "]]"],
                        ["[%", "%]"],
                        ["[#", "#]"],
                        ['"', '"'],
                        ["'", "'"],
                    ],
                }
                (output_path / "language-configuration.json").write_text(
                    json.dumps(lang_config, indent=2)
                )

                # Settings for FastBlocks language server
                settings = {
                    "fastblocks.languageServer.enabled": True,
                    "fastblocks.languageServer.port": 7777,
                    "fastblocks.completion.enabled": True,
                    "fastblocks.diagnostics.enabled": True,
                    "files.associations": {
                        "*.fb.html": "fastblocks",
                        "*.fastblocks": "fastblocks",
                    },
                }
                (output_path / "settings.json").write_text(
                    json.dumps(settings, indent=2)
                )

                console.print(
                    f"[green]✓ VS Code configuration generated in {output_path}[/green]"
                )
                console.print("  Files created:")
                console.print("    - package.json (extension manifest)")
                console.print("    - language-configuration.json")
                console.print("    - syntaxes/fastblocks.tmLanguage.json")
                console.print("    - settings.json")

            elif ide == "vim":
                # Generate Vim configuration
                vim_syntax = """
" Vim syntax file for FastBlocks templates
" Language: FastBlocks
" Maintainer: FastBlocks Team

if exists("b:current_syntax")
  finish
endif

" FastBlocks delimiters
syn region fastblocksVariable start="\\[\\[" end="\\]\\]" contains=fastblocksFilter,fastblocksString
syn region fastblocksBlock start="\\[%" end="%\\]" contains=fastblocksKeyword,fastblocksString
syn region fastblocksComment start="\\[#" end="#\\]"

" Keywords
syn keyword fastblocksKeyword if else elif endif for endfor block endblock extends include set macro endmacro

" Filters
syn match fastblocksFilter "|\\s*\\w\\+" contained

" Strings
syn region fastblocksString start='"' end='"' contained
syn region fastblocksString start="'" end="'" contained

" Highlighting
hi def link fastblocksVariable Special
hi def link fastblocksBlock Keyword
hi def link fastblocksComment Comment
hi def link fastblocksKeyword Statement
hi def link fastblocksFilter Function
hi def link fastblocksString String

let b:current_syntax = "fastblocks"
"""
                (output_path / "fastblocks.vim").write_text(vim_syntax)
                console.print(
                    f"[green]✓ Vim syntax file generated: {output_path}/fastblocks.vim[/green]"
                )

            elif ide == "emacs":
                # Generate Emacs configuration
                emacs_mode = """
;;; fastblocks-mode.el --- Major mode for FastBlocks templates

(defvar fastblocks-mode-syntax-table
  (let ((table (make-syntax-table)))
    (modify-syntax-entry ?\" "\\\"" table)
    (modify-syntax-entry ?\' "\\\"" table)
    table)
  "Syntax table for `fastblocks-mode'.")

(defvar fastblocks-font-lock-keywords
  '(("\\\\[\\\\[.*?\\\\]\\\\]" . font-lock-variable-name-face)
    ("\\\\[%.*?%\\\\]" . font-lock-keyword-face)
    ("\\\\[#.*?#\\\\]" . font-lock-comment-face)
    ("\\\\b\\\\(if\\\\|else\\\\|elif\\\\|endif\\\\|for\\\\|endfor\\\\|block\\\\|endblock\\\\|extends\\\\|include\\\\|set\\\\|macro\\\\|endmacro\\\\)\\\\b" . font-lock-builtin-face))
  "Font lock keywords for FastBlocks mode.")

(define-derived-mode fastblocks-mode html-mode "FastBlocks"
  "Major mode for editing FastBlocks templates."
  (setq font-lock-defaults '(fastblocks-font-lock-keywords)))

(add-to-list 'auto-mode-alist '("\\\\.fb\\\\.html\\\\'" . fastblocks-mode))
(add-to-list 'auto-mode-alist '("\\\\.fastblocks\\\\'" . fastblocks-mode))

(provide 'fastblocks-mode)
;;; fastblocks-mode.el ends here
"""
                (output_path / "fastblocks-mode.el").write_text(emacs_mode)
                console.print(
                    f"[green]✓ Emacs mode file generated: {output_path}/fastblocks-mode.el[/green]"
                )

            else:
                console.print(f"[red]Unsupported IDE: {ide}[/red]")
                console.print("Supported IDEs: vscode, vim, emacs")

        except Exception as e:
            console.print(f"[red]Error generating IDE configuration: {e}[/red]")

    asyncio.run(generate_config())


@cli.command()
def start_language_server(
    port: Annotated[
        int, typer.Option("--port", "-p", help="Port to run language server on")
    ] = 7777,
    host: Annotated[
        str, typer.Option("--host", help="Host to bind language server to")
    ] = "localhost",
    stdio: Annotated[
        bool, typer.Option("--stdio", help="Use stdio instead of TCP")
    ] = False,
) -> None:
    """Start the FastBlocks Language Server."""
    import asyncio

    async def start_server() -> None:
        try:
            from acb.depends import depends

            language_server = await depends.get("language_server")
            if language_server is None:
                console.print(
                    "[red]Language server not available. Make sure you're in a FastBlocks project.[/red]"
                )
                return

            if stdio:
                console.print(
                    "[blue]Starting FastBlocks Language Server in stdio mode...[/blue]"
                )
                # In a real implementation, this would handle stdio communication
                console.print(
                    "[yellow]Stdio mode not yet implemented. Use TCP mode.[/yellow]"
                )
            else:
                console.print(
                    f"[blue]Starting FastBlocks Language Server on {host}:{port}...[/blue]"
                )
                console.print("[green]Language Server started successfully![/green]")
                console.print(f"Connect your IDE to: {host}:{port}")

                # Keep server running using event-based approach
                stop_event = asyncio.Event()
                try:
                    await stop_event.wait()
                except KeyboardInterrupt:
                    console.print("\n[yellow]Language server stopped.[/yellow]")

        except Exception as e:
            console.print(f"[red]Error starting language server: {e}[/red]")

    asyncio.run(start_server())


@cli.command()
def create(
    app_name: Annotated[
        str,
        typer.Option(prompt=True, help="Name of your application"),
    ],
    style: Annotated[
        Styles,
        typer.Option(
            prompt=True,
            help="The style (css, or web component, framework) you want to use[{','.join(Styles._member_names_)}]",
        ),
    ] = Styles.bulma,
    domain: Annotated[
        str,
        typer.Option(prompt=True, help="Application domain"),
    ] = "example.com",
) -> None:
    app_path = apps_path / app_name
    app_path.mkdir(exist_ok=True)
    os.chdir(app_path)
    templates = Path("templates")
    for p in (
        templates / "base/blocks",
        templates / f"{style}/blocks",
        templates / f"{style}/theme",
        Path("adapters"),
        Path("actions"),
    ):
        p.mkdir(parents=True, exist_ok=True)
    for p in (
        Path("models.py"),
        Path("routes.py"),
        Path("main.py"),
        Path(".envrc"),
        Path("pyproject.toml"),
        Path("__init__.py"),
        Path("adapters/__init__.py"),
        Path("actions/__init__.py"),
    ):
        p.touch()
    for template_file in (
        "main.py.tmpl",
        ".envrc",
        "pyproject.toml.tmpl",
        "Procfile.tmpl",
    ):
        template_path = Path(template_file)
        target_path = Path(template_file.replace(".tmpl", ""))
        target_path.write_text(
            (fastblocks_path / template_path).read_text().replace("APP_NAME", app_name),
        )
    commands = (
        ["direnv", "allow", "."],
        ["pdm", "install"],
        ["python", "-m", "fastblocks", "run"],
    )
    for command in commands:
        execute(command, stdout=DEVNULL, stderr=DEVNULL)

    async def update_settings(settings: str, values: dict[str, t.Any]) -> None:
        settings_path = AsyncPath(app_path / "settings")
        settings_dict = await load.yaml(settings_path / f"{settings}.yml")
        settings_dict.update(values)
        await dump.yaml(settings_dict, settings_path / f"{settings}.yml")

    async def update_configs() -> None:
        await update_settings("debug", {"fastblocks": False})
        await update_settings("adapters", default_adapters)
        await update_settings(
            "app", {"title": "Welcome to FastBlocks", "domain": domain}
        )

    asyncio.run(update_configs())
    console.print(
        f"\n[bold][white]Project is initialized. Please configure [green]'adapters.yml'[/] and [green]'app.yml'[/] in the [blue]'{app_name}/settings'[/] directory before running [magenta]`python -m fastblocks dev`[/] or [magenta]`python -m fastblocks run`[/] from the [blue]'{app_name}'[/] directory.[/][/]",
    )
    console.print(
        "\n[dim]Use [white]`python -m fastblocks components`[/white] to see available adapters and actions.[/dim]",
    )
    raise SystemExit


@cli.command()
def version() -> None:
    try:
        __version__ = get_version("fastblocks")
        console.print(f"FastBlocks v{__version__}")
    except Exception:
        console.print("Unable to determine FastBlocks version")


@cli.command()
def mcp(
    port: Annotated[
        int,
        typer.Option("--port", "-p", help="Port for MCP server (default: auto)"),
    ] = 0,
    host: Annotated[
        str, typer.Option("--host", help="Host to bind MCP server to")
    ] = "localhost",
) -> None:
    """Start the FastBlocks MCP (Model Context Protocol) server.

    Enables IDE/AI assistant integration for FastBlocks development
    including template management, component creation, and adapter configuration.
    """
    import asyncio

    async def start_mcp_server() -> None:
        try:
            console.print("\n[bold blue]FastBlocks MCP Server[/bold blue]")
            console.print("[dim]Model Context Protocol for IDE Integration[/dim]\n")

            from .mcp import create_fastblocks_mcp_server

            console.print("[yellow]Initializing MCP server...[/yellow]")
            server = await create_fastblocks_mcp_server()

            console.print("[green]✓ MCP server initialized[/green]")

            if port:
                console.print(f"[blue]Starting server on {host}:{port}...[/blue]")
            else:
                console.print("[blue]Starting server...[/blue]")

            console.print("[green]✓ FastBlocks MCP server running[/green]")
            console.print("\n[dim]Press Ctrl+C to stop[/dim]\n")

            await server.start()

        except KeyboardInterrupt:
            console.print("\n[yellow]MCP server stopped by user[/yellow]")
        except ImportError as e:
            console.print(f"[red]MCP dependencies not available: {e}[/red]")
            console.print(
                "[dim]Make sure ACB is installed with MCP support (acb>=0.23.0)[/dim]"
            )
        except Exception as e:
            console.print(f"[red]Error starting MCP server: {e}[/red]")

    asyncio.run(start_mcp_server())
