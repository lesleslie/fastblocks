"""CI lint: flag ``Counter()`` calls whose ``labelnames`` are outside the allowlist.

Per v6 P1-8 (PromQL-aware metric extraction, NOT substring match) +
Δ40 (pathlib only, no os.path) + Δ41 (``CardinalityMode`` Literal registry):
the cardinality of every Prometheus metric label MUST be bounded at the
type level. The canonical allowlist lives in
:data:`fastblocks.observability._label_allowlist._KNOWN_LABELS`. This
script is the CI gate that prevents a developer from introducing a
``Counter(..., labelnames=("new_label",))`` whose value set is unbounded.

Behaviour
---------

* Walks ``*.py`` files under the target directory (default: current
  working directory). Skips vendored / cached / build paths.
* AST-extracts every ``Counter(name, documentation, labelnames)`` call
  whose ``func`` is the bare name ``Counter`` (i.e. imported as
  ``from fastblocks.observability.counters import Counter``).
* Validates two contracts per call:

  1. The metric ``name`` matches the PromQL identifier regex
     ``^[a-zA-Z_:][a-zA-Z0-9_:]*$`` (per P1-8 — no substring match on
     metric names; the name is structurally validated against the
     grammar of PromQL identifiers).
  2. Every entry in ``labelnames`` is a key of
     ``_KNOWN_LABELS`` (Task 6 registry).

* Exits 1 if any violation is found (each on its own line to
  stderr in ``file:line:`` format). Exits 0 with a summary line on
  stdout when the directory is clean.

Usage
-----

::

    python -m scripts.check_metric_cardinality [path]

With no ``path``, the script walks the current working directory.
"""

from __future__ import annotations

import ast
import dataclasses
import re
import sys
from pathlib import Path

# PromQL identifier grammar (per P1-8). The first character is restricted
# to letter / underscore / colon (colon is reserved for PromQL recording
# rules but is a valid leading char in metric names); subsequent chars
# additionally allow digits. We use anchored full-match so any substring
# match is rejected — this is the "not substring match" requirement of
# P1-8.
PROMQL_METRIC_NAME_REGEX: re.Pattern[str] = re.compile(
    r"^[a-zA-Z_:][a-zA-Z0-9_:]*$",
)

# Directory basenames that MUST NOT be walked. ``pathlib.PurePath.parts``
# would also work, but matching the basename keeps the walker readable
# and matches what ``grep -r --exclude-dir`` does.
SKIP_DIR_NAMES: frozenset[str] = frozenset(
    {
        "__pycache__",
        ".venv",
        "venv",
        ".git",
        ".hg",
        ".svn",
        "build",
        "dist",
        ".eggs",
        ".egg-info",
        "site-packages",
        "node_modules",
        ".mypy_cache",
        ".pytest_cache",
        ".ruff_cache",
        ".crackerjack",
        ".fastblocks",
    },
)


@dataclasses.dataclass(slots=True, kw_only=True, frozen=True)
class Violation:
    """A single lint violation.

    Frozen + slots + kw-only per the project dataclass convention
    (``MetricCardinalityViolation`` is the canonical example in
    ``fastblocks.observability.counters``). Holds enough information
    to emit a greppable ``file:line:`` error message AND to drive the
    test-suite assertions that check the file path / line / label
    contents.

    Attributes:
    ----------
    file : pathlib.Path
        Absolute path to the offending source file.
    line : int
        1-based line number of the ``Counter()`` call site.
    metric_name : str
        Name of the metric the ``Counter()`` call declared. ``"<unknown>"``
        when extraction failed (e.g. ``Counter(name=foo_var, ...)``).
    label : str
        Offending label name. ``"<metric_name>"`` for PromQL-name
        violations (so the test-suite can distinguish them from label
        violations in the same stderr).
    reason : str
        Human-readable reason for the violation.
    """

    file: Path
    line: int
    metric_name: str
    label: str
    reason: str


def _string_constant(node: ast.AST | None) -> str | None:
    """Return the string value of an ``ast.Constant`` literal, else ``None``.

    Non-string constants (``int``, ``Name`` references, ``Call``
    expressions) all return ``None`` so callers can treat them as
    "extraction failed" without special-casing each node type.
    """
    if isinstance(node, ast.Constant) and isinstance(node.value, str):
        return node.value
    return None


def _extract_metric_name(call: ast.Call) -> str | None:
    """Pull the metric ``name`` out of a ``Counter()`` call.

    Supports positional first arg (``Counter("foo", ...)``) and the
    keyword form (``Counter(name="foo", ...)``). Returns ``None``
    when the name is a non-string-literal expression (e.g.
    ``Counter(name=metric_var, ...)``) — the caller treats that as
    a metric-name violation so CI flags it as suspicious.
    """
    if call.args:
        return _string_constant(call.args[0])
    for kw in call.keywords:
        if kw.arg == "name":
            return _string_constant(kw.value)
    return None


def _extract_labelnames(call: ast.Call) -> tuple[str, ...] | None:
    """Pull the ``labelnames`` tuple out of a ``Counter()`` call.

    Three positional-then-keyword forms are supported:

    * ``Counter("foo", "doc", ("a", "b"))`` — positional 3rd arg.
    * ``Counter("foo", "doc", labelnames=("a",))`` — kwarg.
    * ``Counter(name="foo", documentation="doc", labelnames=("a",))`` —
      all-kwargs (the 3rd positional slot is empty).

    Returns ``None`` when the labelnames expression is not a literal
    tuple of strings (e.g. ``Counter("foo", "doc", MY_LABELS)`` or
    ``Counter("foo", "doc", labelnames=[...])`` — both are deliberately
    unhandled because they bypass the cardinality contract).
    """
    # Positional 3rd argument: only valid when the call passes exactly
    # the three documented positional args (name, documentation,
    # labelnames). We do NOT inspect args beyond the 3rd because the
    # signature makes `cardinality_guard` keyword-only.
    if len(call.args) >= 3:
        node = call.args[2]
    else:
        node = None
        for kw in call.keywords:
            if kw.arg == "labelnames":
                node = kw.value
                break

    if node is None:
        # No labelnames supplied — default is () per the Counter signature.
        return ()
    if not isinstance(node, ast.Tuple):
        return None
    labels: list[str] = []
    for elt in node.elts:
        value = _string_constant(elt)
        if value is None:
            return None
        labels.append(value)
    return tuple(labels)


def _check_call(
    call: ast.Call,
    *,
    file_path: Path,
    allowed_labels: frozenset[str],
) -> list[Violation]:
    """Validate one ``Counter()`` call against the cardinality contract.

    Returns the empty list when the call is clean; otherwise one
    ``Violation`` per failure (the metric-name PromQL check and each
    out-of-allowlist label are reported separately).
    """
    line = call.lineno
    metric_name = _extract_metric_name(call)
    labelnames = _extract_labelnames(call)

    violations: list[Violation] = []

    # 1. PromQL name check. Use "<unknown>" when extraction failed so
    #    the report still names the metric (or the unknown sentinel).
    #    A failed extraction also violates the regex (no string matches
    #    ``^[a-zA-Z_:][...]`` for a non-string source), so a single
    #    "metric name" violation is enough.
    effective_name = metric_name if metric_name is not None else "<unknown>"
    if metric_name is None or not PROMQL_METRIC_NAME_REGEX.match(metric_name):
        violations.append(
            Violation(
                file=file_path,
                line=line,
                metric_name=effective_name,
                label="<metric_name>",
                reason=(
                    f"metric name {effective_name!r} violates PromQL "
                    "identifier regex ^[a-zA-Z_:][a-zA-Z0-9_:]*$"
                ),
            ),
        )

    # 2. Label check. ``labelnames=None`` means extraction failed (e.g.
    #    ``Counter("foo", "doc", MY_LABELS)``) — that itself is a
    #    contract violation because the cardinality guard cannot reason
    #    about non-literal labelsets.
    if labelnames is None:
        violations.append(
            Violation(
                file=file_path,
                line=line,
                metric_name=effective_name,
                label="<labelnames>",
                reason=(
                    "labelnames argument is not a literal tuple of "
                    "strings — cannot validate against _KNOWN_LABELS"
                ),
            ),
        )
    else:
        for label in labelnames:
            if label not in allowed_labels:
                violations.append(
                    Violation(
                        file=file_path,
                        line=line,
                        metric_name=effective_name,
                        label=label,
                        reason=(
                            f"label {label!r} not in allowlist (_KNOWN_LABELS.keys())"
                        ),
                    ),
                )

    return violations


def check_file(
    file_path: Path,
    *,
    allowed_labels: frozenset[str],
) -> list[Violation]:
    """AST-walk one ``.py`` file and return its ``Counter()`` violations.

    Files that cannot be read (encoding errors, permission errors) or
    parsed (syntax errors) are silently skipped — the script's job is
    to flag cardinality contract violations, not to compete with the
    project's syntax/encoding linters. An unparsable file would
    surface in those other gates first.
    """
    try:
        source = file_path.read_text(encoding="utf-8")
    except (UnicodeDecodeError, OSError):
        return []
    try:
        tree = ast.parse(source, filename=str(file_path))
    except SyntaxError:
        return []

    violations: list[Violation] = []
    for node in ast.walk(tree):
        if not isinstance(node, ast.Call):
            continue
        if not isinstance(node.func, ast.Name):
            # Attribute calls (``obj.Counter(...)``) are not the canonical
            # ``from fastblocks.observability.counters import Counter``
            # pattern, so they're skipped by design.
            continue
        if node.func.id != "Counter":
            continue
        violations.extend(
            _check_call(node, file_path=file_path, allowed_labels=allowed_labels),
        )
    return violations


def check_directory(
    root: Path,
    *,
    allowed_labels: frozenset[str],
) -> tuple[list[Violation], int]:
    """Walk ``root`` and return (violations, counter_call_count).

    The second element of the tuple is the number of ``Counter()`` calls
    inspected — used for the "All N metric declarations pass" success
    line. Skipped directory basenames are pruned in-place via the
    ``dirnames[:] = ...`` pattern that ``os.walk`` callers use, but
    adapted to ``pathlib.Path.walk`` semantics.
    """
    violations: list[Violation] = []
    counter_count = 0
    for dirpath, dirnames, filenames in root.walk():
        # Prune skip dirs in-place so the walker does not descend into them.
        dirnames[:] = [d for d in dirnames if d not in SKIP_DIR_NAMES]
        for filename in filenames:
            if not filename.endswith(".py"):
                continue
            file_path = dirpath / filename
            # Increment the counter for every matched Counter() call so
            # the success message is meaningful even when the file has
            # # multiple metrics.
            try:
                source = file_path.read_text(encoding="utf-8")
            except (UnicodeDecodeError, OSError):
                continue
            try:
                tree = ast.parse(source, filename=str(file_path))
            except SyntaxError:
                continue
            has_counter = False
            for node in ast.walk(tree):
                if (
                    isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Name)
                    and node.func.id == "Counter"
                ):
                    counter_count += 1
                    has_counter = True
            if has_counter:
                violations.extend(
                    check_file(
                        file_path,
                        allowed_labels=allowed_labels,
                    ),
                )
    return violations, counter_count


def _resolve_target(argv: list[str]) -> Path | None:
    """Return the directory to walk, or ``None`` on CLI error."""
    if argv:
        target = Path(argv[0]).resolve()
    else:
        target = Path.cwd().resolve()
    if not target.exists():
        print(f"error: path does not exist: {target}", file=sys.stderr)
        return None
    if not target.is_dir():
        print(
            f"error: path is not a directory: {target}",
            file=sys.stderr,
        )
        return None
    return target


def main(argv: list[str] | None = None) -> int:
    """CLI entry point — returns the process exit code (0 / 1 / 2)."""
    if argv is None:
        argv = sys.argv[1:]

    target = _resolve_target(argv)
    if target is None:
        return 2

    # Import inside ``main`` so the script remains importable as a module
    # in unit tests without requiring the fastblocks package on ``sys.path``
    # at import time.
    from fastblocks.observability._label_allowlist import _KNOWN_LABELS

    allowed_labels = frozenset(_KNOWN_LABELS.keys())

    violations, counter_count = check_directory(
        target,
        allowed_labels=allowed_labels,
    )

    if violations:
        for v in violations:
            print(f"{v.file}:{v.line}: {v.reason}", file=sys.stderr)
        print(
            f"\n{len(violations)} violation(s) found across "
            f"{counter_count} Counter() declaration(s).",
            file=sys.stderr,
        )
        return 1

    print(
        f"All {counter_count} metric declarations pass cardinality check",
    )
    return 0


__all__ = [
    "PROMQL_METRIC_NAME_REGEX",
    "SKIP_DIR_NAMES",
    "Violation",
    "check_directory",
    "check_file",
    "main",
]


if __name__ == "__main__":
    sys.exit(main())
