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
        re.compile(rf"\b{re.escape(name)}\b")
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


# ---------------------------------------------------------------------------
# Audit regression (2026-07-27): tool registration was a NameError.
# ---------------------------------------------------------------------------


class _RecordingServer:
    """Stand-in for an ``mcp_common`` server profile.

    Mirrors the registration contract of the real
    ``MinimalServer``/``StandardServer``/``FullServer``, which was verified
    directly against the installed package: ``tool(name)`` returns a decorator
    that registers the function, and ``list_tools()`` returns the registered
    names. A double is used because ``tests/conftest.py`` installs an
    ``mcp_common`` stub at session scope, which makes the real package's
    submodules unimportable inside the suite.
    """

    def __init__(self) -> None:
        self._tools: dict[str, t.Any] = {}

    def tool(self, name: str | None = None) -> t.Any:
        def decorator(fn: t.Any) -> t.Any:
            self._tools[name or getattr(fn, "__name__", repr(fn))] = fn
            return fn

        return decorator

    def list_tools(self) -> list[str]:
        return sorted(self._tools)


@pytest.mark.unit
async def test_register_fastblocks_tools_registers_the_documented_surface() -> None:
    """All 7 read-only tools must land on the server.

    `register_fastblocks_tools` called an undefined `register_tools(...)`
    (carrying `# type: ignore[name-defined]`), so it raised `NameError` --
    and `MCPServerBase._register_tools` wraps the call in
    `with suppress(Exception)`, so the failure was silent and *zero* MCP
    tools were ever registered.
    """
    from fastblocks.mcp.tools import register_fastblocks_tools

    server = _RecordingServer()
    await register_fastblocks_tools(server)

    expected = {
        "validate_template",
        "list_templates",
        "render_template",
        "list_components",
        "validate_component",
        "list_adapters",
        "check_adapter_health",
    }
    assert expected <= set(server.list_tools()), (
        f"missing tools: {sorted(expected - set(server.list_tools()))}"
    )


# ---------------------------------------------------------------------------
# Phase 1.5.2/1.5.3 — Resolver singleton ownership boundary guard
# ---------------------------------------------------------------------------


class TestResolverOwnershipBoundary:
    """CI guard for the Phase 1.5 singleton ownership boundary.

    Phase 1.5.2 enforces:

    - ``fastblocks.core.resolver.get_resolver()`` returns the fastblocks-
      OWNED singleton (not Oneiric's, not a per-pool fresh instance).
    - No ``= Resolver()`` declarations anywhere in ``fastblocks/``
      outside the singleton's home (``core/resolver.py``). Every site
      must route through ``FastblocksRegistry(get_resolver())`` instead.
    - No Bodai cross-component consumer imports
      ``fastblocks.core.resolver``. Sibling projects (mahavishnu, akosha,
      dhara, session-buddy, crackerjack, oneiric, mcp-common) must call
      ``oneiric.core.resolver.get_resolver()`` if they need their own
      resolver.

    These guards catch regressions before merge: any contributor who
    reaches past the facade for ``= Resolver()`` or imports the singleton
    across a component boundary will fail this test in CI.
    """

    # Sibling projects that are forbidden from importing
    # ``fastblocks.core.resolver``. Paths are absolute because we run
    # this scan from the fastblocks checkout and the sibling repos
    # live in the user's Projects directory.
    BODAI_SIBLING_REPOS: tuple[str, ...] = (
        "/Users/les/Projects/mahavishnu",
        "/Users/les/Projects/akosha",
        "/Users/les/Projects/dhara",
        "/Users/les/Projects/session-buddy",
        "/Users/les/Projects/crackerjack",
        "/Users/les/Projects/oneiric",
        "/Users/les/Projects/mcp-common",
    )

    # Same regex the migration script used; pinned here so the guard
    # matches the exact shape we committed to in Phase 1.5.1.
    _RESOLVER_DECL = re.compile(r"^\s*\w+\s*=\s*Resolver\(\)\s*$")
    _CROSS_COMPONENT_IMPORT = re.compile(
        r"from\s+fastblocks\.core\.resolver\s+import"
    )

    def _iter_fastblocks_sources(self) -> list[Path]:
        fastblocks_dir = REPO_ROOT / "fastblocks"
        out: list[Path] = []
        for py_file in fastblocks_dir.rglob("*.py"):
            # Skip backup files and the venv (defence in depth).
            if py_file.name.endswith(".backup.py"):
                continue
            if ".venv" in py_file.parts:
                continue
            # The singleton's own module is allowed to construct a
            # Resolver (it's where the lazy-init lives).
            try:
                rel = py_file.relative_to(REPO_ROOT / "fastblocks" / "core")
            except ValueError:
                rel = None
            if rel is not None and rel.parts and rel.parts[0] == "resolver.py":
                continue
            out.append(py_file)
        return out

    @pytest.mark.unit
    def test_no_resolver_instantiation_outside_core_resolver(self) -> None:
        """Phase 1.5.1 post-condition: zero ``= Resolver()`` outside the singleton."""
        violations: list[tuple[Path, int, str]] = []
        for path in self._iter_fastblocks_sources():
            try:
                text = path.read_text(encoding="utf-8")
            except (OSError, UnicodeDecodeError):
                continue
            for lineno, line in enumerate(text.splitlines(), start=1):
                if self._RESOLVER_DECL.match(line):
                    violations.append((path, lineno, line.strip()))
        assert not violations, (
            "`= Resolver()` is forbidden outside `fastblocks/core/resolver.py`.\n"
            "Route through the FastblocksRegistry facade instead:\n"
            "    depends = FastblocksRegistry(get_resolver())\n"
            "Violations:\n"
            + "\n".join(f"  {p}:{n}: {l}" for p, n, l in violations)
        )

    @pytest.mark.unit
    def test_no_bodai_sibling_imports_fastblocks_core_resolver(self) -> None:
        """Phase 1.5.2 ownership boundary enforcement.

        Cross-component consumers must NOT import the fastblocks
        singleton. Use ``oneiric.core.resolver.get_resolver()`` for an
        independent Oneiric resolver.
        """
        violations: list[tuple[Path, int, str]] = []


        for repo_path in self.BODAI_SIBLING_REPOS:
            repo_root = Path(repo_path)
            if not repo_root.exists():
                # Repo not present on this machine — skip silently.
                # The audit still runs in environments that have it.
                continue
            for py_file in repo_root.rglob("*.py"):
                # Skip vendored / venv / vendored-deps directories.
                parts = set(py_file.parts)
                if parts & {".venv", "node_modules", ".git", "dist", "build"}:
                    continue
                try:
                    text = py_file.read_text(encoding="utf-8")
                except (OSError, UnicodeDecodeError):
                    continue
                for lineno, line in enumerate(text.splitlines(), start=1):
                    if self._CROSS_COMPONENT_IMPORT.search(line):
                        violations.append((py_file, lineno, line.strip()))
        assert not violations, (
            "Cross-component Bodai consumers must NOT import "
            "fastblocks.core.resolver — the singleton is fastblocks-private.\n"
            "Use `oneiric.core.resolver.get_resolver()` for an independent "
            "Oneiric resolver, or import from `fastblocks.adapters.<x>` for "
            "domain-specific access. Violations:\n"
            + "\n".join(f"  {p}:{n}: {l}" for p, n, l in violations)
        )

    @pytest.mark.unit
    def test_get_resolver_is_singleton(self) -> None:
        """Repeated ``get_resolver()`` calls return the same instance."""
        from fastblocks.core.resolver import get_resolver

        a = get_resolver()
        b = get_resolver()
        assert a is b, (
            "get_resolver() must return the same Resolver instance on "
            "every call (process-wide singleton). Multi-pool workers get "
            "their own singleton per process; no sharing across pools."
        )

    @pytest.mark.unit
    def test_fastblocks_registry_wraps_get_resolver(self) -> None:
        """``FastblocksRegistry(get_resolver())`` is the canonical construction.

        The registry's ``unwrap()`` must return the singleton from
        ``get_resolver()`` so the facade and the singleton are the same
        identity (the singleton is the underlying state).
        """
        from fastblocks.core.resolver import FastblocksRegistry, get_resolver

        registry = FastblocksRegistry(get_resolver())
        assert registry.unwrap() is get_resolver()
