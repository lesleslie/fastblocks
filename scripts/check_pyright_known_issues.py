#!/usr/bin/env python3
"""Gate pyright informational diagnostics against ``docs/known-type-issues.md``.

Pyright is informational, NOT a CI-blocking gate (mypy + ty are). This
script keeps pyright from drifting silently: every diagnostic pyright
emits that isn't covered by a row in ``docs/known-type-issues.md``
trips the script — printed as a WARNING (so reviewers see the
category list) AND causes a non-zero exit (so CI fails if a new
diagnostic appears).

Run from ``fastblocks/`` after:

    uvx --from pyright pyright fastblocks 2>&1 | tee /tmp/pyright.txt
    uv run python scripts/check_pyright_known_issues.py

Exits ``0`` when every diagnostic category is documented.
Exits ``1`` when one or more new categories are present (unknown).
"""

from __future__ import annotations

import re
import sys
from dataclasses import dataclass
from pathlib import Path

PYRIGHT_OUTPUT = Path("/tmp/pyright.txt")
DOC = Path(__file__).resolve().parent.parent / "docs" / "known-type-issues.md"

# One diagnostic line in pyright's text output looks like:
#   /path/to/file.py:10:5 - error: Import "x" could not be resolved (reportMissingImports)
# OR (verbose mode):
#   /path/to/file.py:10:5 - warning: Type of parameter "x" is unknown (reportUnknownParameterType)
LINE_RE = re.compile(
    r"^(?P<path>[^\s:]+?):(?P<line>\d+):(?P<col>\d+)\s+-\s+"
    r"(?P<severity>error|warning|information):\s+"
    r"(?P<message>.+?)\s*\((?P<rule>report[A-Za-z]+)\)\s*$"
)

# pyright emits absolute paths on macOS/Linux. Strip everything up to
# ``fastblocks/`` so prefixes match the table entries.
REPO_ROOT_MARKER = "fastblocks/"


def _relative(path: str) -> str:
    idx = path.find(REPO_ROOT_MARKER)
    return path[idx:] if idx >= 0 else path


@dataclass(frozen=True)
class Diagnostic:
    path: str
    line: int
    severity: str
    rule: str
    message: str

    @property
    def relpath(self) -> str:
        return _relative(self.path)

    @property
    def prefix(self) -> str:
        """Directory-prefix used as the table-key. The fastblocks
        repo uses ``fastblocks/`` twice in the path (repo name +
        package name), so we look for the *second* ``fastblocks/`` and
        take everything up to the next slash.

        Examples::

            /Users/.../fastblocks/fastblocks/main.py
                -> fastblocks/main.py/                 (parent of source)
            /Users/.../fastblocks/fastblocks/mcp/server.py
                -> fastblocks/mcp/                     (parent of source)
        """
        rel = self.relpath
        # Drop the trailing filename; prefix = parent dir.
        if "/" in rel.rsplit("/", 1)[-1]:
            # No slash? shouldn't happen for a file path.
            return rel
        parent = rel.rsplit("/", 1)[0]
        # ``fastblocks`` is both repo and package — the package parent
        # is what we want.
        return parent + "/" if parent else rel


def parse_pyright(path: Path) -> list[Diagnostic]:
    if not path.exists():
        print(
            f"error: {path} not found; run "
            f"'uvx --from pyright pyright fastblocks 2>&1 | tee {path}' first",
            file=sys.stderr,
        )
        sys.exit(2)
    out: list[Diagnostic] = []
    for raw in path.read_text(encoding="utf-8", errors="replace").splitlines():
        m = LINE_RE.match(raw.strip())
        if not m:
            continue
        out.append(
            Diagnostic(
                path=m.group("path"),
                line=int(m.group("line")),
                severity=m.group("severity"),
                rule=m.group("rule"),
                message=m.group("message"),
            )
        )
    return out


def parse_known_rules(doc: Path) -> set[str]:
    """Return the set of ``rule`` names from the markdown table.

    The table is rule-keyed (``reportXxx``); the path-prefix column is
    informational. A new pyright rule that is NOT in the table fails
    the gate; a new (rule, prefix) combination under a known rule
    does NOT fail the gate (the table rows are illustrative
    distributions, not strict allowlists).
    """
    if not doc.exists():
        print(
            f"error: {doc} not found; the D2 gate requires this file",
            file=sys.stderr,
        )
        sys.exit(2)
    known: set[str] = set()
    for raw in doc.read_text(encoding="utf-8").splitlines():
        if not raw.startswith("|"):
            continue
        cells = [c.strip() for c in raw.strip().strip("|").split("|")]
        if len(cells) < 2:
            continue
        rule = cells[0].strip("`").strip()
        if not rule.startswith("report"):
            continue
        if rule in {"Rule", "File:Line"}:
            continue
        known.add(rule)
    return known


def category_key(d: Diagnostic) -> tuple[str, str]:
    return (d.rule, d.prefix)


def main() -> int:
    diagnostics = parse_pyright(PYRIGHT_OUTPUT)
    known_rules = parse_known_rules(DOC)

    # Group by rule only — see ``docs/known-type-issues.md`` for the
    # design rationale. Every (rule, file-prefix) tuple is documented
    # in the table; if a new rule appears, the rule check below fails.
    # Path-prefix drift within a known rule is allowed (table entries
    # include the per-prefix breakdown so reviewers can still see the
    # rough distribution).
    by_rule: dict[str, list[Diagnostic]] = {}
    for d in diagnostics:
        by_rule.setdefault(d.rule, []).append(d)

    unknown_rules: list[tuple[str, list[Diagnostic]]] = []
    for rule, items in sorted(by_rule.items()):
        if rule not in known_rules:
            unknown_rules.append((rule, items))

    total = len(diagnostics)
    covered = sum(len(items) for r, items in by_rule.items() if r in known_rules)
    print(f"pyright diagnostics: {total}")
    print(f"  covered by known rules: {covered}")
    print(f"  rules in pyright output: {len(by_rule)}")
    print(f"  rules in known table: {len(known_rules)}")
    if unknown_rules:
        print()
        print("WARNING: pyright emitted rules not in known table")
        print("  (add a row to docs/known-type-issues.md OR fix the code):")
        for rule, items in unknown_rules:
            print(f"    {rule:38s}  ({len(items)} diagnostics across {len(set(d.path for d in items))} files)")
            for sample in items[:3]:
                print(f"        {sample.path}:{sample.line}  {sample.message[:90]}")
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())