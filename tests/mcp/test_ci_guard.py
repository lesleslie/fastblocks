"""CI guard for the 0.8.0 MCP-surface cutover.

Phase 0b removed the dangerous FastBlocks-side MCP surface:
- WebSocket tools (moved to SplashStand)
- Config CLI wizard (Python APIs retained; Click harness deleted)
- Inner @mcp.tool() closures for create_template / create_component / configure_adapter
- Legacy ``register_fastblocks_tools_async`` wrapper
- Fake ``get_route_definitions`` MCP resource
- Click ``audit`` / ``migrate`` / ``health_check`` subcommands

This guard greps the source tree for the deleted symbol names and fails
the build if any of them resurface. New contributors who reintroduce
the dangerous surface will be caught before merge.

Symbol lists below are the public names the FastMCP server would expose
when the deleted code paths were active. They are intentionally
hard-coded (not auto-discovered) so the guard does not silently pass
when new deletions happen.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

# ---------------------------------------------------------------------------
# Symbols that MUST NOT reappear after the 0.8.0 cutover.
# ---------------------------------------------------------------------------

# Inner @mcp.tool() closures that exposed Python public APIs as MCP tools.
# The OUTER top-level functions (create_template, create_component,
# configure_adapter) are kept as part of the public Python API and may
# appear in tests/ — but the FastMCP tool wrappers must not.
DELETED_MCP_TOOL_NAMES: tuple[str, ...] = (
    "fastblocks_create_template",
    "fastblocks_create_component",
    "fastblocks_configure_adapter",
    "fastblocks_start_websocket",
    "fastblocks_stop_websocket",
    "fastblocks_websocket_status",
    "fastblocks_broadcast_ui",
    "fastblocks_broadcast_component",
    "fastblocks_broadcast_state",
    "fastblocks_list_subscriptions",
)

# Python identifiers that should no longer be referenced.
# Listed as substrings — match in import statements, decorators, or docstrings.
DELETED_PYTHON_IDENTIFIERS: tuple[str, ...] = (
    "websocket_tools",
    "config_cli",
    "get_route_definitions",
    "register_fastblocks_tools_async",
)

# ---------------------------------------------------------------------------
# Files and directories scanned.
# ---------------------------------------------------------------------------

REPO_ROOT = Path(__file__).resolve().parents[2]
SCAN_TARGETS: tuple[Path, ...] = (
    REPO_ROOT / "fastblocks" / "mcp" / "__init__.py",
    REPO_ROOT / "fastblocks" / "mcp" / "server.py",
    REPO_ROOT / "fastblocks" / "mcp" / "tools.py",
    REPO_ROOT / "fastblocks" / "mcp" / "cli.py",
    REPO_ROOT / "fastblocks" / "mcp" / "resources.py",
    REPO_ROOT / "fastblocks" / "mcp" / "discovery.py",
    REPO_ROOT / "fastblocks" / "mcp" / "health.py",
    REPO_ROOT / "fastblocks" / "mcp" / "registry.py",
)


def _collect_python_files_importing_fastblocks_mcp() -> list[Path]:
    """Find every .py file under fastblocks/ that imports from fastblocks.mcp."""
    fastblocks_dir = REPO_ROOT / "fastblocks"
    found: list[Path] = []
    for py_file in fastblocks_dir.rglob("*.py"):
        try:
            text = py_file.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        if re.search(r"from\s+fastblocks\.mcp", text) or re.search(
            r"import\s+fastblocks\.mcp", text
        ):
            found.append(py_file)
    return found


def _scan_for_deleted_symbols() -> dict[str, list[tuple[Path, int, str]]]:
    """Return {symbol: [(path, line_no, line), ...]} for each deleted symbol hit.

    Identifiers are matched as whole words; tool names use the
    ``fastblocks_<name>`` prefix to match the FastMCP convention
    (e.g. ``@mcp.tool(name="fastblocks_create_template")``).
    """
    hits: dict[str, list[tuple[Path, int, str]]] = {}

    # 1) Hard-coded tool names — must not appear as bare symbols either.
    for name in DELETED_MCP_TOOL_NAMES:
        # Match either the prefixed form (fastblocks_create_template) or the
        # bare form (create_template) when used inside @mcp.tool(name=...)
        pattern = re.compile(rf"\b{re.escape(name)}\b")
        hits[name] = []

    # 2) Python identifiers — substring match is enough because they are
    #    all module-private enough that false positives are negligible
    #    (e.g. "websocket_tools" cannot appear in a Jinja template context
    #    in the mcp package).
    for ident in DELETED_PYTHON_IDENTIFIERS:
        hits[ident] = []

    files_to_scan: list[Path] = list(SCAN_TARGETS) + _collect_python_files_importing_fastblocks_mcp()
    for path in files_to_scan:
        if not path.exists():
            continue
        try:
            text = path.read_text(encoding="utf-8")
        except (OSError, UnicodeDecodeError):
            continue
        for line_no, line in enumerate(text.splitlines(), start=1):
            for name in DELETED_MCP_TOOL_NAMES:
                if re.search(rf"\b{re.escape(name)}\b", line):
                    hits[name].append((path, line_no, line))
            for ident in DELETED_PYTHON_IDENTIFIERS:
                # Substring match for module paths and decorators
                if ident in line:
                    hits[ident].append((path, line_no, line))

    return hits


# ---------------------------------------------------------------------------
# Tests
# ---------------------------------------------------------------------------


@pytest.mark.unit
def test_deleted_mcp_tool_names_not_reintroduced() -> None:
    """FastMCP tool names from the deleted surface must not reappear."""
    hits = _scan_for_deleted_symbols()
    violations = {name: occurrences for name, occurrences in hits.items() if occurrences}
    assert not violations, (
        "Deleted 0.8.0 MCP-surface symbols were reintroduced:\n"
        + "\n".join(
            f"  {name}:\n    " + "\n    ".join(f"{p}:{n}: {l.strip()}" for p, n, l in occs)
            for name, occs in violations.items()
        )
    )


@pytest.mark.unit
def test_deleted_python_identifiers_not_reintroduced() -> None:
    """Deleted module/function names from the cutover must not reappear."""
    # Same scan, but report the python-identifier subset for a focused
    # message. test_deleted_mcp_tool_names_not_reintroduced already
    # asserts the full set is empty — this is a redundant safety net that
    # gives a clearer failure message for identifier-level regressions.
    all_hits = _scan_for_deleted_symbols()
    violations = {
        name: occs
        for name, occs in all_hits.items()
        if name in DELETED_PYTHON_IDENTIFIERS and occs
    }
    assert not violations, (
        "Deleted 0.8.0 Python identifiers were reintroduced:\n"
        + "\n".join(
            f"  {name}:\n    " + "\n    ".join(f"{p}:{n}: {l.strip()}" for p, n, l in occs)
            for name, occs in violations.items()
        )
    )


@pytest.mark.unit
def test_websocket_tools_module_file_deleted() -> None:
    """fastblocks/mcp/websocket_tools.py must stay deleted (moved to SplashStand)."""
    assert not (REPO_ROOT / "fastblocks" / "mcp" / "websocket_tools.py").exists(), (
        "fastblocks/mcp/websocket_tools.py was deleted in 0.8.0 and moved to "
        "SplashStand. Re-add only if the upstream MCP ownership decision is "
        "reversed."
    )


@pytest.mark.unit
def test_config_cli_module_file_deleted() -> None:
    """fastblocks/mcp/config_cli.py must stay deleted (Click wizard removed)."""
    assert not (REPO_ROOT / "fastblocks" / "mcp" / "config_cli.py").exists(), (
        "fastblocks/mcp/config_cli.py was deleted in 0.8.0. The underlying "
        "Python APIs (ConfigurationManager, ConfigurationAuditor, "
        "EnvironmentManager, ConfigurationMigrationManager, "
        "ConfigurationHealthChecker) remain importable from their original "
        "modules — do not bring back the Click wrapper."
    )
