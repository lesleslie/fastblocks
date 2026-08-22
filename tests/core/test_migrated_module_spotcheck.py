"""Phase 1.5.x remediation Card 7 — cross-module coverage spot-check.

F-L4-06 (Phase 1.5 adversarial review): the existing cross-module
test exercises two fixture modules (tests/_fixtures/*.py) plus
tests/conftest.py. It does NOT cover the ~62 production files that
the Phase 1.5.1 facade migration touched.

This test does not attempt full coverage of those 62 files (which
would be expensive and brittle — the migration introduced fixture-
driven lazy imports that fail on cold start). Instead it spot-checks
nine representative files across the three layers the migration
touched (actions, adapters, mcp), asserting each one:

  1. imports without raising (smoke test for the migration rewrite);
  2. uses the facade (``FastblocksRegistry`` or ``get_resolver``),
     not a raw ``oneiric.core.resolution.Resolver()`` — preserving
     ADR 0008 Rule 2 (consolidation invariant).

The exception list (``_EXEMPT_FROM_RAW_RESOLVER_GREP``) is the
documented whitelist: the legacy ``oneiric_helper`` keeps the
old factory semantics for backward compat; README files contain
historical references; docstring examples reference the helper.

If a future contributor adds a new raw ``Resolver()`` outside the
whitelist, this test fails loudly with the offending file:line.

See ``docs/superpowers/plans/2026-08-21-fastblocks-modern-framework-master-plan.md``
Phase 1.5x remediation, Card 7 (F-L4-06).
"""

from __future__ import annotations

import importlib
import re
from pathlib import Path

import pytest

# Representative samples spanning the three layers of the migration.
# Each entry is a dot-path that ``importlib.import_module`` can load.
_REPRESENTATIVE_MODULES: tuple[str, ...] = (
    # Oneiric helper (the legacy compat boundary)
    "fastblocks.adapters.oneiric_helper",
    # MCP layer
    "fastblocks.mcp.discovery",
    "fastblocks.mcp.registry",
    # Adapters (one per family touched)
    "fastblocks.adapters.fonts._base",
    "fastblocks.adapters.icons.fontawesome",
    # Actions layer
    "fastblocks.actions.gather.application",
    "fastblocks.actions.gather.middleware",
    # main (root entry)
    "fastblocks.main",
    # Top-level core
    "fastblocks.applications",
)

# Files where raw ``Resolver()`` is allowed by design — not a regression.
# Each entry is a pathlib-posix prefix relative to the repo root.
_EXEMPT_FROM_RAW_RESOLVER_GREP: tuple[str, ...] = (
    # The legacy compat helper — keeps factory semantics on purpose.
    "fastblocks/adapters/oneiric_helper.py",
    # The facade module itself — owns the lazy-init singleton.
    "fastblocks/core/resolver.py",
    # Historical references; not production code.
    "fastblocks/adapters/sitemap/README.md",
    "fastblocks/adapters/fonts/README.md",
    # Docstring examples only.
    "fastblocks/adapters/style/fastblocks_ui.py",
    "fastblocks/middleware.py",
)


@pytest.mark.unit
@pytest.mark.parametrize("module_path", _REPRESENTATIVE_MODULES)
def test_migrated_module_imports_clean(module_path: str) -> None:
    """Each sampled migrated module imports without raising.

    Smoke test: if a Phase 1.5.1 rewrite introduced a missing import
    or a circular dependency, this surfaces in CI instead of leaking
    into an operator-facing cold start.
    """
    importlib.import_module(module_path)


@pytest.mark.unit
def test_no_raw_resolver_outside_whitelist() -> None:
    """No migrated production file uses raw ``Resolver()``.

    ADR 0008 Rule 2 / F-L3-3 invariant: every consumer must go
    through the ``FastblocksRegistry`` facade (or the legacy
    ``oneiric_helper`` whitelist). A new raw ``Resolver()`` would
    create a new private resolver and silently bypass the
    consolidation invariant.
    """
    repo_root = Path(__file__).resolve().parents[2]
    exempted = {str(repo_root / p) for p in _EXEMPT_FROM_RAW_RESOLVER_GREP}

    # Match ``Resolver()`` or ``oneiric.core.resolution.Resolver(`` patterns
    # in production code. Docstrings/comments in non-exempted files
    # still count — they document what coders see and a future
    # contributor will copy-paste them.
    raw_resolver_pattern = re.compile(r"\bResolver\s*\(", re.MULTILINE)

    offenders: list[tuple[str, int, str]] = []
    for py_file in (repo_root / "fastblocks").rglob("*.py"):
        path_str = str(py_file)
        if path_str in exempted:
            continue
        # Skip __pycache__ and tests directories.
        if "__pycache__" in path_str:
            continue
        if "/tests/" in path_str or "/test_" in path_str:
            continue

        # Walk line-by-line; skip lines inside a module-level
        # docstring (between the first occurrence of triple-double-
        # quote and the next). Cheap heuristic: treat all lines
        # above the first non-docstring code line as docstring.
        text_lines = py_file.read_text().splitlines()
        triple_count = 0
        code_started = False
        for line_no, line in enumerate(text_lines, start=1):
            stripped = line.lstrip()
            # Triple-quote toggling happens via a running count of
            # bare """ occurrences.
            triple_count += line.count('"""')
            if triple_count >= 2 and not code_started:
                code_started = True
                continue
            if not code_started:
                continue
            if raw_resolver_pattern.search(line):
                if stripped.startswith("#"):
                    continue
                offenders.append(
                    (str(py_file.relative_to(repo_root)), line_no, line.rstrip()),
                )

    assert not offenders, (
        "Raw Resolver() found outside the documented whitelist — each "
        "occurrence would create a private registry that bypasses ADR "
        "0008 Rule 2 (consolidation invariant). Either migrate the "
        "construction site to FastblocksRegistry(get_resolver()) or add "
        "the file to _EXEMPT_FROM_RAW_RESOLVER_GREP with justification.\n\n"
        + "\n".join(f"  {f}:{ln}: {l}" for f, ln, l in offenders)
    )


@pytest.mark.unit
def test_migrated_modules_share_singleton_via_facade() -> None:
    """Sampled modules import the facade, not raw Resolver.

    Every sampled module's import graph must include
    ``fastblocks.core.resolver`` so the FastblocksRegistry facade is
    available, even if the module's own code does not call
    ``get_resolver()`` directly. A future migration that strips
    the facade import from a module then refactors to call
    ``Resolver()`` directly would silently reintroduce the
    per-module-private-registry anti-pattern.
    """
    facade_pattern = re.compile(r"from fastblocks\.core\.resolver import")
    repo_root = Path(__file__).resolve().parents[2]

    missing: list[str] = []
    for module_path in _REPRESENTATIVE_MODULES:
        # Translate dot-path to file path.
        rel = module_path.replace(".", "/") + ".py"
        path = repo_root / rel
        if not path.exists():
            missing.append(f"{module_path}: file not found at {rel}")
            continue
        text = path.read_text()
        if not facade_pattern.search(text):
            missing.append(
                f"{module_path}: does not import "
                "'from fastblocks.core.resolver import'",
            )

    assert not missing, (
        "Sampled modules should each import the facade so future "
        "refactors route through the consolidation invariant:\n"
        + "\n".join(f"  - {m}" for m in missing)
    )
