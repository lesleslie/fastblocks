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

# Populated in subsequent phases. Empty for the skeleton.
PROHIBITED_IMPORTS: tuple[str, ...] = ()
PROHIBITED_CLI_COMMANDS: tuple[str, ...] = ()
PROHIBITED_MCP_TOOLS: tuple[str, ...] = ()
PROHIBITED_PORTS: tuple[str, ...] = ()


def _iter_doc_text() -> list[tuple[Path, str]]:
    """Return (path, text) for every doc under DOCS_TO_SCAN.

    Skips archive directories (``docs/archive/``, ``docs/baselines/``,
    ``docs/superpowers/notes/``) and ``.git/``. Walks directories recursively.
    """
    out: list[tuple[Path, str]] = []
    skip_substrings = ("/archive/", "/baselines/", "/superpowers/notes/", "/.git/")
    for entry in DOCS_TO_SCAN:
        if entry.is_file():
            out.append((entry, entry.read_text(encoding="utf-8", errors="replace")))
            continue
        for path in entry.rglob("*.md"):
            spath = str(path)
            if any(s in spath for s in skip_substrings):
                continue
            out.append((path, path.read_text(encoding="utf-8", errors="replace")))
    return out


@pytest.mark.parametrize("prohibited_symbol", PROHIBITED_IMPORTS)
def test_no_prohibited_imports(prohibited_symbol: str) -> None:
    """No doc may reference a removed/prohibited import path."""
    for path, text in _iter_doc_text():
        assert prohibited_symbol not in text, (
            f"Found prohibited import {prohibited_symbol!r} in {path.relative_to(REPO_ROOT)}"
        )
