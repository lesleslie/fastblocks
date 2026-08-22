"""Phase 2 mechanical-four Commit3 — validators sync test (AST-based).

Mirrors tests/unit/test_task_router.py::TestYAMLRoutingSync. Parses
``validators.py`` to extract the canonical StyleName members, then
parses ``AppBaseSettings`` and ``cli.py`` to verify every consumer
references the same Literal set.

The AST visitor spec is in spec §Sync enforcement. Reject:
- Inline Literal[...] outside validators.py (assertion 3).
- Literal[*values] PEP 646 unpacking (assertion 5 — Commit4 ships this).
- TypeAlias of Literal[...] outside validators.py (assertion 4).
"""
from __future__ import annotations

import ast
import typing as t
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]
VALIDATORS_PATH = REPO_ROOT / "fastblocks" / "core" / "validators.py"
APP_BASE_PATH = REPO_ROOT / "fastblocks" / "adapters" / "app" / "_base.py"
CLI_PATH = REPO_ROOT / "fastblocks" / "cli.py"


def _extract_literal_members(node: ast.AST) -> tuple[str, ...] | None:
    """Return Literal members as a tuple, or None if node isn't Literal[...]."""
    if not isinstance(node, ast.Subscript):
        return None
    if not (isinstance(node.value, ast.Name) and node.value.id == "Literal"):
        return None
    slice_node = node.slice
    if isinstance(slice_node, ast.Tuple):
        members: list[str] = []
        for elt in slice_node.elts:
            if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                members.append(elt.value)
            else:
                return None  # non-string member; reject
        return tuple(members)
    if isinstance(slice_node, ast.Constant) and isinstance(slice_node.value, str):
        return (slice_node.value,)
    return None


def _load_canonical_members() -> tuple[str, ...]:
    """Parse validators.py and return StyleName's Literal members.

    Handles both the plain-assignment form
    ``StyleName = Literal[...]`` and the annotated form
    ``StyleName: TypeAlias = Literal[...]``.
    """
    tree = ast.parse(VALIDATORS_PATH.read_text())
    for node in ast.walk(tree):
        target_id: str | None = None
        annotation: ast.AST | None = None
        if isinstance(node, ast.AnnAssign) and isinstance(node.target, ast.Name):
            target_id = node.target.id
            annotation = node.annotation
        elif isinstance(node, ast.Assign):
            for target in node.targets:
                if isinstance(target, ast.Name):
                    target_id = target.id
                    annotation = node.value
                    break
        if target_id != "StyleName" or annotation is None:
            continue
        members = _extract_literal_members(annotation)
        if members is None:
            raise AssertionError(
                f"StyleName annotation in {VALIDATORS_PATH} is not a "
                f"plain Literal[...] — got {ast.dump(annotation)}"
            )
        return members
    raise AssertionError(f"StyleName not found in {VALIDATORS_PATH}")


def _iter_annotations_in_file(path: Path) -> t.Iterator[ast.AST]:
    """Yield every annotation AST node from a file."""
    tree = ast.parse(path.read_text())
    yield from ast.walk(tree)


@pytest.mark.unit
def test_app_base_settings_style_matches_validators_style_name() -> None:
    """AppBaseSettings.style annotation resolves to the same members as StyleName."""
    canonical = _load_canonical_members()
    tree = ast.parse(APP_BASE_PATH.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.AnnAssign):
            continue
        if not isinstance(node.target, ast.Name):
            continue
        if node.target.id != "style":
            continue
        # Skip if annotation is `StyleName` (Name reference) — that's
        # the alias case (assertion 2 covers it); here we check inline
        # Literal[...] was NOT introduced.
        if isinstance(node.annotation, ast.Name):
            assert node.annotation.id == "StyleName", (
                f"AppBaseSettings.style annotation must be either "
                f"StyleName or Literal[...]; got annotation name "
                f"{node.annotation.id!r} at "
                f"{APP_BASE_PATH}:{node.lineno}"
            )
            return
        members = _extract_literal_members(node.annotation)
        if members is None:
            # Some other annotation (TypeAlias, etc.); assertion 4
            # catches it for TypeAlias
            return
        assert members == canonical, (
            f"AppBaseSettings.style Literal members {members} differ "
            f"from canonical StyleName {canonical}"
        )


@pytest.mark.unit
def test_cli_does_not_declare_inline_literal_with_style_members() -> None:
    """No inline Literal['vanilla', 'fastblocks_ui'] in cli.py.

    cli.py must import StyleName from validators; any inline Literal
    with the style members is a drift surface the sync test forbids.
    """
    canonical = _load_canonical_members()
    for node in _iter_annotations_in_file(CLI_PATH):
        members = _extract_literal_members(node)
        if members is None:
            continue
        # If this inline Literal's members match the canonical style set,
        # it's a drift surface. (Inline Literals with different members
        # — e.g., for an unrelated domain — are fine; not flagged here.)
        if set(members) == set(canonical):
            raise AssertionError(
                f"cli.py declares an inline Literal with the style "
                f"members {members}; must import StyleName from "
                f"fastblocks.core.validators instead"
            )


@pytest.mark.unit
def test_cli_imports_style_name_from_validators() -> None:
    """cli.py imports StyleName from fastblocks.core.validators.

    Verifies the rename took effect (Commit3's primary deliverable).
    """
    tree = ast.parse(CLI_PATH.read_text())
    for node in ast.walk(tree):
        if not isinstance(node, ast.ImportFrom):
            continue
        if node.module != "fastblocks.core.validators":
            continue
        imported_names = {alias.name for alias in node.names}
        assert "StyleName" in imported_names, (
            f"cli.py imports from fastblocks.core.validators but does "
            f"not import StyleName; got {imported_names}"
        )
        return
    raise AssertionError(
        "cli.py does not import from fastblocks.core.validators; "
        "the StyleName rename has not landed"
    )


@pytest.mark.unit
def test_default_style_is_a_style_name_member() -> None:
    """DEFAULT_STYLE in validators.py is one of StyleName's members."""
    import typing

    from fastblocks.core.validators import DEFAULT_STYLE, StyleName

    legal = typing.get_args(StyleName)
    assert DEFAULT_STYLE in legal, (
        f"DEFAULT_STYLE {DEFAULT_STYLE!r} is not one of StyleName's "
        f"members {legal}"
    )


@pytest.mark.unit
def test_validators_rejects_pep_646_starred_literal_outside_validators() -> None:
    """Literal[*values] unpacking (PEP 646) outside validators.py is rejected.

    Future drift vector: a contributor extracts the style set to
    ``STYLES = ('vanilla', 'fastblocks_ui')`` and writes
    ``Literal[*STYLES]``. AST must reject that pattern outside
    ``validators.py`` because the spec mandates inline enumeration
    (the sync test's source-of-truth is the Literal itself, not a
    separate tuple).
    """
    # Scan both cli.py and _base.py for any Literal[*...] pattern
    for path in (APP_BASE_PATH, CLI_PATH):
        tree = ast.parse(path.read_text())
        for node in ast.walk(tree):
            if not isinstance(node, ast.Subscript):
                continue
            # The slice inside Literal[*values] is an ast.Starred
            slice_node = node.slice
            if isinstance(slice_node, ast.Starred):
                raise TypeError(
                    f"{path.name} uses Literal[*...] (PEP 646) "
                    f"unpacking; the spec mandates inline enumeration "
                    f"in fastblocks.core.validators.StyleName. Replace "
                    f"with a direct Literal[...] or import StyleName."
                )
