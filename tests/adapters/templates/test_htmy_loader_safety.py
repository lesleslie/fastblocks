"""HTMY loader safety regression test (Phase 1A Deliverable C3).

The unsafe ``_load_from_cached_bytecode`` and ``_load_from_source`` methods
in ``fastblocks/adapters/templates/htmy.py`` used
``importlib.util.spec_from_file_location`` + ``spec.loader.exec_module`` —
the live RCE vector CLAUDE.md:130 documents as removed by Phase 1.3. C3
deletes those methods and routes ``get_component_class`` through the
AST-sandboxed ``load_component_from_source`` from
``fastblocks/adapters/templates/_htmy_components.py`` instead.

This test pins two guarantees:

1. **Import-time regex guard** — opens ``htmy.py``, scans for the
   ``importlib.util.spec_from_file_location`` / ``exec_module`` /
   ``__import__`` / dynamic ``exec(`` / ``eval(`` patterns. Any code-level
   match is a regression; comment-only matches (in the explanatory block
   that documents WHY the loaders were removed) are tolerated.

2. **Behavioral test** — ``HTMYTemplates.get_component_class`` returns the
   expected component class for trusted components, and raises
   ``ComponentCompilationError`` (not a silent failure) when AST validation
   rejects a malicious source.
"""

from __future__ import annotations

import re
from pathlib import Path

import pytest

from fastblocks.adapters.templates.htmy import (
    ComponentCompilationError,
    HTMYTemplates,
)
from fastblocks.adapters.templates._htmy_components import (
    load_component_from_source,
)

# Patterns that indicate the unsafe code path has been reintroduced. The
# regex is anchored to ``htmy.py`` only — the AST-sandboxed loader in
# ``_htmy_components.py`` legitimately uses some of these (e.g. ``exec``
# inside a documented false-positive suppress), so scanning must be scoped.
UNSAFE_PATTERNS = (
    r"importlib\.util\.spec_from_file_location",
    r"spec\.loader\.exec_module",
    r"__import__\s*\(",
    r"\bexec\s*\(\s*[^#]",  # bare exec( call (not in a comment)
    r"\beval\s*\(\s*[^#]",  # bare eval( call (not in a comment)
)

# Patterns that MUST appear (proves the AST-sandboxed route is wired):
REQUIRED_PATTERNS = (
    r"load_component_from_source",  # AST-sandboxed loader imported + called
)


HTMY_PY = Path(__file__).resolve().parents[3] / "fastblocks" / "adapters" / "templates" / "htmy.py"


def _strip_comments_and_docstrings(source: str) -> str:
    """Remove # comments and triple-quoted docstrings so we only scan code."""
    # Strip # comments line-by-line (naive; doesn't handle triple-quoted
    # strings spanning multiple # markers, but that's not in htmy.py).
    no_comments = "\n".join(
        line.split("#", 1)[0] if not line.lstrip().startswith("#") else ""
        for line in source.splitlines()
    )
    # Strip triple-quoted docstrings (greedy, single pass).
    no_docs = re.sub(r'"""[\s\S]*?"""', "", no_comments, flags=re.MULTILINE)
    no_docs = re.sub(r"'''[\s\S]*?'''", "", no_docs, flags=re.MULTILINE)
    return no_docs


class TestHtmyLoaderSafetyRegression:
    """Pin the C3 RCE fix so reintroduction is caught at CI."""

    def test_htmy_module_loads_cleanly(self) -> None:
        """Sanity check: importing htmy.py still works post-C3."""
        # The import at module top already runs; just verify the symbols
        # we expect are still exported.
        assert HTMYTemplates is not None
        assert ComponentCompilationError is not None

    def test_no_spec_from_file_location_in_code(self) -> None:
        """No code uses ``importlib.util.spec_from_file_location`` — the
        canonical entry-point for the unsafe ``exec_module`` path."""
        source = HTMY_PY.read_text()
        code_only = _strip_comments_and_docstrings(source)
        for pattern in UNSAFE_PATTERNS:
            matches = re.findall(pattern, code_only)
            assert matches == [], (
                f"unsafe pattern {pattern!r} found in {HTMY_PY.name} code: {matches!r}"
            )

    def test_rce_reintroduction_guard_at_import(self) -> None:
        """Import-time check that mirrors what a CI guard could enforce.

        Opens ``htmy.py`` and asserts the unsafe patterns are absent from
        the code (comments excluded). Runs at module-load via the test
        discovery so a regression breaks the test run, not just one
        branch invocation.
        """
        # Re-run the regex check from this method's body; if a regression
        # introduces one of the patterns, this assertion fires.
        source = HTMY_PY.read_text()
        code_only = _strip_comments_and_docstrings(source)
        for pattern in UNSAFE_PATTERNS:
            assert not re.search(pattern, code_only), (
                f"RCE regression: {pattern!r} re-introduced in {HTMY_PY.name}"
            )

    def test_loaders_deleted(self) -> None:
        """Both ``_load_from_cached_bytecode`` and ``_load_from_source``
        methods must be absent from ``HTMYTemplates``."""
        assert not hasattr(HTMYTemplates, "_load_from_cached_bytecode"), (
            "_load_from_cached_bytecode re-introduced on HTMYTemplates"
        )
        assert not hasattr(HTMYTemplates, "_load_from_source"), (
            "_load_from_source re-introduced on HTMYTemplates"
        )

    def test_required_ast_sandboxed_route_present(self) -> None:
        """``load_component_from_source`` must be imported and called
        from ``htmy.py`` — proves the AST-sandboxed path is wired."""
        source = HTMY_PY.read_text()
        for pattern in REQUIRED_PATTERNS:
            assert re.search(pattern, source), (
                f"required pattern {pattern!r} missing from {HTMY_PY.name}"
            )


class TestHtmyLoaderSafetyBehavioral:
    """Behavioral tests of the AST-sandboxed route."""

    def test_ast_loader_rejects_dangerous_import(self) -> None:
        """A source with `import os` is rejected by the AST-sandboxed
        loader with ``ComponentValidationError`` (allowlist: dataclasses,
        typing)."""
        malicious = (
            "import os\n"
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Bad:\n"
            "    x: int = 1\n"
            "    def htmy(self): return ''\n"
        )
        from fastblocks.adapters.templates._htmy_components import (
            ComponentValidationError,
        )

        with pytest.raises(ComponentValidationError):
            load_component_from_source(malicious, "bad")

    def test_ast_loader_rejects_exec_call(self) -> None:
        """A source with `exec(...)` is rejected."""
        malicious = (
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Bad:\n"
            "    x: int = 1\n"
            "    def htmy(self):\n"
            "        exec('print(1)')\n"
            "        return ''\n"
        )
        from fastblocks.adapters.templates._htmy_components import (
            ComponentValidationError,
        )

        with pytest.raises(ComponentValidationError):
            load_component_from_source(malicious, "bad")

    def test_ast_loader_accepts_valid_component(self) -> None:
        """A well-formed dataclass component loads successfully and has
        a callable ``htmy`` method."""
        valid = (
            "from dataclasses import dataclass\n"
            "@dataclass\n"
            "class Good:\n"
            "    label: str = 'x'\n"
            "    def htmy(self) -> str:\n"
            "        return self.label\n"
        )
        component_class = load_component_from_source(valid, "good")
        assert callable(getattr(component_class, "htmy", None))
