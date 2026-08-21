"""Phase 1.5.1 migration: `name = Resolver()` → `name = FastblocksRegistry(get_resolver())`.

Per ruff-cleanup-script-dangers.md, the script:
- Uses AST for detection (not bare regex on multi-line)
- Applies a SINGLE-LINE substitution per match (no re.S, no cross-line)
- Validates every modified file with ``ast.parse()`` before write
- Removes unused ``Resolver`` from ``from oneiric.core.resolution import ...``
  (only if no other ``Resolver`` reference remains — type annotations keep it)
- Adds ``from fastblocks.core.resolver import FastblocksRegistry, get_resolver``
  in the right import group (first-party), respecting
  ``known-first-party = ["fastblocks"]``
- Is idempotent: re-running on a migrated file is a no-op

Run::

    python scripts/migrate_resolver_to_fastblocks_registry.py [--dry-run]

After running, verify with::

    git grep -nE '^\\s*\\w+\\s*=\\s*Resolver\\(\\)\\s*$' fastblocks/

should return 0 hits outside ``fastblocks/core/resolver.py``.
"""

from __future__ import annotations

import argparse
import ast
import re
import sys
from pathlib import Path

ROOT = Path("fastblocks")
EXCLUDE = {ROOT / "core" / "resolver.py"}
RESOLVER_BLANK_CALL = re.compile(r"^(\s*)(\w+)\s*=\s*Resolver\(\)\s*$")
ONEIRIC_RESOLVER_IMPORT = re.compile(
    r"^from oneiric\.core\.resolution import (?P<names>[^\n]+)$",
    re.MULTILINE,
)


def find_resolver_calls(source: str) -> list[tuple[int, str]]:
    """Return [(lineno, varname), ...] for any ``name = Resolver()`` at any scope.

    Includes module-, class-, and function-scope calls; the substitution is
    uniform so scope does not matter. We trust the AST to identify the
    targets correctly; the text-level substitution anchors to the
    specific (line, varname) tuple the AST produced.
    """
    tree = ast.parse(source)
    out: list[tuple[int, str]] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Assign):
            continue
        call = node.value
        if not (
            isinstance(call, ast.Call)
            and isinstance(call.func, ast.Name)
            and call.func.id == "Resolver"
            and not call.args
            and not call.keywords
        ):
            continue
        if len(node.targets) != 1 or not isinstance(node.targets[0], ast.Name):
            continue
        out.append((node.lineno, node.targets[0].id))
    return out


def uses_resolver_as_value(source: str) -> bool:
    """Return True if ``Resolver`` appears in source outside ``Resolver()`` calls.

    Used to decide whether ``Resolver`` can be dropped from the
    ``from oneiric.core.resolution import ...`` import without ruff
    flagging it as a missing name.
    """
    tree = ast.parse(source)
    for node in ast.walk(tree):
        if isinstance(node, ast.Name) and node.id == "Resolver":
            # ``Resolver()`` is Name(ctx=Load) but its parent is Call; we
            # already filter those out at the call-site level. The simpler
            # check is "any Name(id='Resolver') anywhere" — false positives
            # are fine because the conservative path is to KEEP the import.
            return True
        if isinstance(node, ast.Attribute) and node.attr == "Resolver":
            return True
    return False


def strip_resolver_from_oneiric_import(source: str) -> str:
    """Drop ``Resolver`` from the oneiric import if it's the only name.

    Line-based manipulation (no regex-span stripping) so we don't
    accidentally collapse adjacent lines by double-stripping newlines.
    Per ruff-cleanup-script-dangers.md warning #3, appending code "after
    the last import" via regex span arithmetic can swallow surrounding
    newlines; line-based rewrites preserve file structure.

    Leading whitespace is allowed because some sites import inside
    ``try:`` blocks (e.g. ``fastblocks/actions/gather/routes.py``),
    where the import is indented 4 spaces.
    """
    lines = source.splitlines(keepends=True)
    out: list[str] = []
    for line in lines:
        m = re.match(
            r"^\s*from oneiric\.core\.resolution import (?P<names>.+?)\s*$",
            line.rstrip("\n").rstrip("\r"),
        )
        if not m:
            out.append(line)
            continue
        raw_names = m.group("names")
        # Strip paren-wrapped imports to bare names
        if raw_names.startswith("(") and raw_names.endswith(")"):
            raw_names = raw_names[1:-1]
        names = [n.strip() for n in raw_names.split(",") if n.strip()]
        if "Resolver" not in names:
            out.append(line)
            continue
        remaining = [n for n in names if n != "Resolver"]
        if not remaining:
            # Drop the entire line — keep its newline off the output.
            continue
        joined = ", ".join(remaining)
        trailing = "\n" if line.endswith("\n") else ""
        # Preserve the original leading whitespace so indented imports
        # stay indented (e.g. inside ``try:`` blocks).
        leading = line[: len(line) - len(line.lstrip())]
        out.append(
            f"{leading}from oneiric.core.resolution import {joined}{trailing}"
        )
    return "".join(out)


def already_imports_resolver_facade(source: str) -> bool:
    return "from fastblocks.core.resolver import" in source


def add_resolver_facade_import(source: str) -> str:
    """Insert ``from fastblocks.core.resolver import FastblocksRegistry, get_resolver``.

    Placement rule: directly after the LAST COMPLETE top-level import,
    treating paren-wrapped ``from X import (a, b, c)`` blocks as a
    single multi-line import. The import block is bounded at the top
    by ``from __future__ import ...`` and at the bottom by the first
    non-import, non-blank, non-comment line. Module docstrings
    (triple-quoted strings at the very top) are skipped so the
    ``from __future__`` line that often follows them is correctly
    identified as the first import anchor.

    Per ruff-cleanup-script-dangers.md warning #3, naive "append after
    the last ``import``/``from`` line" logic lands INSIDE paren-wrapped
    import blocks. We track paren depth to skip continuation lines
    within a multi-line ``from X import (...)`` import.
    """
    lines = source.splitlines(keepends=True)
    new_import = (
        "from fastblocks.core.resolver import FastblocksRegistry, get_resolver\n"
    )

    future_end = -1
    last_import_end = -1
    in_paren_import = False
    paren_depth = 0
    in_docstring = False
    docstring_quote: str | None = None

    for i, line in enumerate(lines):
        stripped = line.strip()

        # Skip module docstring (simple triple-quote heuristic — sufficient
        # for the patterns we encounter; pathological edge cases like a
        # raw triple-quoted string at module top would need ast parsing).
        if in_docstring:
            if docstring_quote and docstring_quote in line:
                in_docstring = False
                docstring_quote = None
            continue
        if stripped.startswith('"""') or stripped.startswith("'''"):
            quote = '"""' if stripped.startswith('"""') else "'''"
            if stripped.count(quote) < 2:
                in_docstring = True
                docstring_quote = quote
            # Single-line docstrings (opens and closes on same line) — skip.
            continue

        if stripped.startswith("from __future__ import"):
            future_end = i + 1
            continue

        if in_paren_import:
            paren_depth += line.count("(") - line.count(")")
            if paren_depth <= 0:
                in_paren_import = False
                last_import_end = i
            continue

        if stripped.startswith(("import ", "from ")):
            # Detect paren-wrapped multi-line imports.
            open_count = line.count("(")
            close_count = line.count(")")
            if open_count > close_count:
                in_paren_import = True
                paren_depth = open_count - close_count
                if paren_depth <= 0:
                    in_paren_import = False
                    last_import_end = i
                continue
            last_import_end = i
            continue

        if stripped == "" or stripped.startswith("#"):
            continue
        # First non-import, non-blank, non-comment line — stop scanning.
        break

    if last_import_end >= 0:
        insert_idx = last_import_end + 1
    elif future_end >= 0:
        insert_idx = future_end
    else:
        insert_idx = 0

    lines.insert(insert_idx, new_import)
    return "".join(lines)


def migrate_file(path: Path) -> int:
    """Apply the migration to one file. Returns substitutions made."""
    source = path.read_text()
    matches = find_resolver_calls(source)
    if not matches:
        return 0

    lines = source.splitlines(keepends=True)
    # Reverse so line numbers stay valid as we mutate.
    for lineno, varname in reversed(matches):
        old_line = lines[lineno - 1]
        # Match the entire line: indent + ``varname = Resolver()`` +
        # ``tail`` (whitespace, optional ``# ...`` comment, AND the
        # line-ending newline when ``keepends=True``).
        #
        # We anchor with ``^...\\Z`` (start-of-string + end-of-string)
        # rather than ``$`` because Python ``re``'s ``$`` matches just
        # BEFORE a trailing ``\n``, which would drop the newline and
        # silently merge the next line onto this one — exactly the
        # bug class warned about in ``ruff-cleanup-script-dangers.md``
        # item #2 (unanchored cross-line matches).
        #
        # ``re.DOTALL`` makes ``.*`` greedy match newlines so the entire
        # trailing content is captured in one group. Safe here because
        # we are anchored at both ends; per the memory, the danger of
        # DOTALL is unanchored patterns spanning unrelated code.
        pattern = re.compile(
            rf"^(\s*){re.escape(varname)}\s*=\s*Resolver\(\)(?P<tail>.*)\Z",
            re.DOTALL,
        )
        m = pattern.match(old_line)
        if not m:
            raise RuntimeError(
                f"{path}:{lineno}: regex could not match line {old_line!r}"
            )
        new_line = (
            f"{m.group(1)}{varname} = FastblocksRegistry(get_resolver())"
            f"{m.group('tail')}"
        )
        if new_line == old_line:
            raise RuntimeError(
                f"{path}:{lineno}: regex could not substitute line {old_line!r}"
            )
        lines[lineno - 1] = new_line
    new_source = "".join(lines)

    # Drop Resolver from the oneiric import only if it is no longer used.
    if not uses_resolver_as_value(new_source):
        new_source = strip_resolver_from_oneiric_import(new_source)

    # Add the facade import if missing.
    if not already_imports_resolver_facade(new_source):
        new_source = add_resolver_facade_import(new_source)

    # Validate the result parses.
    try:
        ast.parse(new_source)
    except SyntaxError as exc:
        raise RuntimeError(
            f"{path}: ast.parse failed after edit: {exc}"
        ) from exc

    path.write_text(new_source)
    return len(matches)


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dry-run", action="store_true")
    args = parser.parse_args()

    total_files = 0
    total_subs = 0
    errors: list[str] = []

    for path in sorted(ROOT.rglob("*.py")):
        if path in EXCLUDE:
            continue
        if path.name.endswith(".backup.py") or ".venv" in path.parts:
            continue
        try:
            n = migrate_file(path) if not args.dry_run else _dry_count(path)
        except RuntimeError as exc:
            errors.append(str(exc))
            continue
        if n:
            tag = "[DRY] " if args.dry_run else ""
            print(f"{tag}{path}: {n} substitution(s)")
            total_files += 1
            total_subs += n

    print(
        f"\nTotal: {total_subs} substitution(s) across {total_files} file(s)"
    )
    if errors:
        print("\nERRORS:")
        for e in errors:
            print(f"  {e}")
        return 1
    return 0


def _dry_count(path: Path) -> int:
    """Dry-run helper: report what would change without writing."""
    return len(find_resolver_calls(path.read_text()))


if __name__ == "__main__":
    sys.exit(main())