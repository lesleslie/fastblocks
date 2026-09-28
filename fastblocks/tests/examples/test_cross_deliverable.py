"""Cross-deliverable smoke tests — verifies each example boots in isolation.

REQ-P2-INT-001 — Each deliverable has main.py + tests/ directory
REQ-P2-INT-002 — D9 grep gate: no kelp/webawesome/acb usage anywhere
"""
from __future__ import annotations

import re
from pathlib import Path

import pytest

EXAMPLES = [
    ("starter", Path("/tmp/test-app")),
    ("landing", Path("/Users/les/Projects/fastblocks/examples/landing")),
    ("htmy-hybrid", Path("/Users/les/Projects/fastblocks/examples/htmy-hybrid")),
]

# Pattern matches actual kelp/webawesome usage: token references (imports,
# identifiers, type annotations). Excludes plain prose mentions such as
# "kelp was removed in Phase 1A" or "webawesome" appearing in a docstring
# description of historical context. Identifiers must appear as Python words.
_USAGE_TOKENS = re.compile(
    r"\b(kelp|webawesome)\b\s*[(=:,)]"   # identifier followed by call/assign/arg
    r"|\bimport\s+(acb|kelp|webawesome)\b"  # actual import statement
    r"|\bfrom\s+(acb|kelp|webawesome)\b",  # actual from-import statement
    re.IGNORECASE,
)


@pytest.mark.parametrize("name,path", EXAMPLES)
def test_example_has_main_py(name: str, path: Path) -> None:
    # req: REQ-P2-INT-001
    if not path.exists():
        pytest.skip(f"{name}: path does not exist (e.g. starter tested via CLI)")
    assert (path / "main.py").exists(), f"{name}: missing main.py"


@pytest.mark.parametrize("name,path", EXAMPLES)
def test_example_has_tests_dir(name: str, path: Path) -> None:
    # req: REQ-P2-INT-001
    if not path.exists():
        pytest.skip(f"{name}: path does not exist (e.g. starter tested via CLI)")
    assert (path / "tests").is_dir(), f"{name}: missing tests/"


@pytest.mark.parametrize("name,path", EXAMPLES)
def test_example_no_kelp_webawesome_acb(name: str, path: Path) -> None:
    """D9 grep gate — must hold across all deliverables."""
    # req: REQ-P2-INT-002
    if not path.exists():
        pytest.skip(f"{name}: path does not exist (e.g. starter tested via CLI)")
    for py in path.rglob("*.py"):
        text = py.read_text()
        match = _USAGE_TOKENS.search(text)
        assert match is None, (
            f"{name}/{py}: contains banned token {match.group(0)!r}"
        )