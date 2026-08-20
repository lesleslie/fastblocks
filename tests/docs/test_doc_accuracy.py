"""Doc accuracy CI guard for FastBlocks.

These tests protect prose-level correctness in user-facing docs:
- No ``acb.*`` imports (Phase 3.1 migration removed the ACB dependency).
- No fabricated CLI subcommands or MCP tool names.
- No env-var names that disagree with ``git grep`` of source.
- No phantom filenames.
- Coverage claims must match pyproject.toml.

Each test reads a curated list of docs under test, greps the source tree
for the same symbols, and asserts parity. Pattern follows
``tests/mcp/test_ci_guard.py``.
"""
from __future__ import annotations

import re
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DOCS_TO_SCAN: tuple[Path, ...] = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "QWEN.md",
    REPO_ROOT / "RULES.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "docs",
    REPO_ROOT / "fastblocks",
)

# (1) No ACB imports — Phase 3.1 removed the ACB dependency entirely.
PROHIBITED_IMPORTS: tuple[str, ...] = (
    "from acb.",
    "import acb",
    "from acb.depends",
    "from acb.adapters",
    "from acb.config",
    "from acb.actions",
    "from acb.services",
    "from acb.mcp",
    "from acb.workflows",
    "from acb.events",
    "register_pkg(",
    "uv add acb[",
)

# (2) No fabricated CLI subcommands or flags.
PROHIBITED_CLI_COMMANDS: tuple[str, ...] = (
    "python -m fastblocks serve",
    "fastblocks serve",
    "--comprehensive",
    " -x -t ",  # not a real flag combo
)

# (3) No fabricated MCP tool names (Phase 0b/0.8.0 removed them).
#
# Note: the 4 WebSocket server tools (``fastblocks_start_websocket`` and
# friends) are guarded separately by ``tests/mcp/test_ci_guard.py``,
# which scans source code. They are LEGITIMATELY mentioned in
# migration docs (``docs/migrations/0.7-to-0.8.md``) and CI guard
# documentation (``CLAUDE.md``), so the doc-accuracy guard skips them.
PROHIBITED_MCP_TOOLS: tuple[str, ...] = (
    "execute_fastblocks",
    "get_job_progress",
    "get_comprehensive_status",
    "broadcast_ui_update",
    "broadcast_component_render",
)

# (4) No fabricated ports.
PROHIBITED_PORTS: tuple[str, ...] = (
    "ws://localhost:8675",
    "localhost:8675",
)

# (5) Phantom filenames that don't exist on disk.
PHANTOM_FILENAMES: tuple[str, ...] = (
    "docs/ACB_GUIDE.md",
    "docs/MIGRATION-0.17.0.md",
    "docs/ACB_DEPENDS_PATTERNS.md",
)


def _iter_doc_text() -> list[tuple[Path, str]]:
    """Return (path, text) for every doc under DOCS_TO_SCAN.

    Skips archive directories (``docs/archive/``, ``docs/baselines/``,
    ``docs/superpowers/notes/``, ``docs/superpowers/plans/``,
    ``docs/superpowers/specs/``) and ``.git/``. Walks directories recursively.

    Also skips ``CHANGELOG.md`` because it is a HISTORICAL record —
    it documents what code was in past releases, including pre-Phase 3.1
    references to ``acb.*`` imports and historical coverage ratchet
    numbers (e.g. ``88.93%``) that predate the current floor. User-
    authorized exemption (2026-08-19).

    Plans, specs, and SDD briefs are skipped because they describe the
    prohibited symbols as remediation targets — scanning them would
    always fail.
    """
    out: list[tuple[Path, str]] = []
    skip_substrings = (
        "/archive/",
        "/baselines/",
        "/superpowers/notes/",
        "/superpowers/plans/",
        "/superpowers/specs/",
        "/.git/",
        "/.superpowers/",
    )
    skip_files: set[Path] = {
        REPO_ROOT / "CHANGELOG.md",
        REPO_ROOT / "docs" / "TYPE_SYSTEM_MIGRATION.md",
        REPO_ROOT / "docs" / "LESSONS_LEARNED.md",
    }
    for entry in DOCS_TO_SCAN:
        if entry.is_file():
            if entry in skip_files:
                continue
            out.append((entry, entry.read_text(encoding="utf-8", errors="replace")))
            continue
        for path in entry.rglob("*.md"):
            spath = str(path)
            if any(s in spath for s in skip_substrings):
                continue
            if path in skip_files:
                continue
            out.append((path, path.read_text(encoding="utf-8", errors="replace")))
    return out


@pytest.mark.parametrize("prohibited_symbol", PROHIBITED_IMPORTS)
def test_no_prohibited_imports(prohibited_symbol: str) -> None:
    """No doc may reference a removed/prohibited import path."""
    pattern = re.compile(rf"\b{re.escape(prohibited_symbol)}\b")
    for path, text in _iter_doc_text():
        assert not pattern.search(text), (
            f"Found prohibited import {prohibited_symbol!r} in {path.relative_to(REPO_ROOT)}"
        )


@pytest.mark.parametrize("prohibited_symbol", PROHIBITED_CLI_COMMANDS)
def test_no_prohibited_cli(prohibited_symbol: str) -> None:
    pattern = re.compile(rf"\b{re.escape(prohibited_symbol)}\b")
    for path, text in _iter_doc_text():
        assert not pattern.search(text), (
            f"Found fabricated CLI {prohibited_symbol!r} in {path.relative_to(REPO_ROOT)}"
        )


@pytest.mark.parametrize("prohibited_symbol", PROHIBITED_MCP_TOOLS)
def test_no_prohibited_mcp_tool(prohibited_symbol: str) -> None:
    pattern = re.compile(rf"\b{re.escape(prohibited_symbol)}\b")
    for path, text in _iter_doc_text():
        assert not pattern.search(text), (
            f"Found fabricated MCP tool {prohibited_symbol!r} in {path.relative_to(REPO_ROOT)}"
        )


@pytest.mark.parametrize("prohibited_port", PROHIBITED_PORTS)
def test_no_prohibited_port(prohibited_port: str) -> None:
    pattern = re.compile(rf"\b{re.escape(prohibited_port)}\b")
    for path, text in _iter_doc_text():
        assert not pattern.search(text), (
            f"Found fabricated port {prohibited_port!r} in {path.relative_to(REPO_ROOT)}"
        )


@pytest.mark.parametrize("phantom_path", PHANTOM_FILENAMES)
def test_no_phantom_filenames(phantom_path: str) -> None:
    """No doc may reference a phantom path that doesn't exist on disk.

    Scans every doc for a substring match against the phantom filename.
    Fails if any doc still references it.
    """
    for path, text in _iter_doc_text():
        assert phantom_path not in text, (
            f"{phantom_path} referenced in {path.relative_to(REPO_ROOT)} but does not exist"
        )


def test_no_phantom_adapter_paths() -> None:
    """Adapter README references to ``main.py`` must resolve to ``default.py``."""
    # (Audit finding: adapters/{app,routes}/README.md reference main.py.)
    for adapter in ("app", "routes"):
        readme = REPO_ROOT / f"fastblocks/adapters/{adapter}/README.md"
        if not readme.exists():
            continue
        text = readme.read_text(encoding="utf-8")
        assert "main.py" not in text, (
            f"{readme.relative_to(REPO_ROOT)} still references main.py; "
            "actual file is default.py"
        )


def test_env_var_names_match_source() -> None:
    """Every ``FASTBLOCKS_*`` env var mentioned in docs must appear in source.

    Catches the WEBSOCKET_GUIDE class of bug where the doc names one env
    var and the code reads a different one.
    """
    env_var_re = re.compile(r"\bFASTBLOCKS_[A-Z_]+\b")
    doc_env_vars: set[str] = set()
    for _path, text in _iter_doc_text():
        for match in env_var_re.findall(text):
            doc_env_vars.add(match)
    source_env_vars: set[str] = set()
    for path in (REPO_ROOT / "fastblocks").rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in env_var_re.findall(text):
            source_env_vars.add(match)

    # If a doc names an env var that the source never reads, the doc is wrong.
    orphaned = doc_env_vars - source_env_vars
    assert not orphaned, (
        f"Docs reference env vars that source never reads: {sorted(orphaned)}"
    )


def test_coverage_target_consistency() -> None:
    """Every coverage % in docs must match pyproject.toml fail_under."""
    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    match = re.search(r"--cov-fail-under=([\d.]+)", pyproject)
    if match is None:
        pytest.skip("Could not find --cov-fail-under in pyproject.toml")
    floor = float(match.group(1))
    pct_re = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
    tolerance = 0.1
    for path, text in _iter_doc_text():
        for pct_match in pct_re.finditer(text):
            candidate = float(pct_match.group(1))
            if not (5.0 <= candidate <= 100.0):
                continue
            ctx_start = max(0, pct_match.start() - 50)
            ctx = text[ctx_start : pct_match.end() + 5].lower()
            if "coverage" not in ctx and "cov" not in ctx:
                continue
            assert abs(candidate - floor) < tolerance, (
                f"{path.relative_to(REPO_ROOT)} claims coverage {candidate}% "
                f"but pyproject.toml floor is {floor}%"
            )


def test_no_backup_json_in_git() -> None:
    """Backup files must never reach git history."""
    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    leaked = [line for line in result.stdout.splitlines() if line.endswith(".backup.json")]
    assert not leaked, (
        f".backup.json files are tracked in git: {leaked}"
    )
