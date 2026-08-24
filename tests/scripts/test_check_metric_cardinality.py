"""Tests for ``scripts/check_metric_cardinality.py``.

Per v6 P1-8 (PromQL-aware metric extraction, NOT substring match) +
Δ40 (pathlib only, no os.path) + Δ41 (CardinalityMode Literal registry):
the cardinality check script walks Python source trees, AST-extracts
``Counter(name, documentation, labelnames=(...))`` calls, and verifies
every labelname is a key in :data:`fastblocks.observability._label_allowlist._KNOWN_LABELS`.
The metric name itself must also match the PromQL identifier regex
``^[a-zA-Z_:][a-zA-Z0-9_:]*$``.

Each test creates a temporary Python file under ``tmp_path`` and runs
``python -m scripts.check_metric_cardinality`` against the directory,
asserting on the exit code, stdout, and stderr of the subprocess.
"""

from __future__ import annotations

import re
import subprocess
import sys
from pathlib import Path

import pytest

# Path to the script under test — relative to the repo root so the test
# can invoke it as ``python -m scripts.check_metric_cardinality``. The
# repo root is two parents above this file (…/tests/scripts/<file>.py).
REPO_ROOT = Path(__file__).resolve().parents[2]
SCRIPT_MODULE = "scripts.check_metric_cardinality"


def _run_script(target_dir: Path) -> subprocess.CompletedProcess[str]:
    """Invoke the cardinality check script as a module against ``target_dir``.

    Runs ``sys.executable -m scripts.check_metric_cardinality <dir>`` from
    the repo root so ``scripts/`` is importable as a package. Sets
    ``PYTHONPATH`` to the repo root so the package is importable even
    when the CWD differs from REPO_ROOT.
    """
    import os

    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(REPO_ROOT)
    )
    return subprocess.run(
        [sys.executable, "-m", SCRIPT_MODULE, str(target_dir)],
        capture_output=True,
        text=True,
        check=False,
        cwd=REPO_ROOT,
        env=env,
    )


def _write_counter_file(
    tmp_path: Path,
    *,
    counter_call: str,
    filename: str = "metrics.py",
) -> Path:
    """Materialise a temp Python file with a single Counter() call.

    The wrapper provides the import line and the Counter class call so
    the test body only has to specify the call shape under test.
    """
    file_path = tmp_path / filename
    file_path.write_text(
        f"from fastblocks.observability.counters import Counter\n{counter_call}\n",
        encoding="utf-8",
    )
    return file_path


# ---------------------------------------------------------------------------
# 1. Bad label → exit 1 + file:line in stderr
# ---------------------------------------------------------------------------


def test_bad_label_positional_exits_one_with_file_line(tmp_path: Path) -> None:
    """A Counter call with a label outside _KNOWN_LABELS exits 1.

    The error message MUST be ``<file>:<line>: label "X" not in
    allowlist`` so the lint output is greppable by CI tooling.
    """
    file_path = _write_counter_file(
        tmp_path,
        counter_call='Counter("foo", "doc", ("bogus_label",))',
        filename="bad_positional.py",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 1, (
        f"expected exit 1 for bogus label; got exit={result.returncode}\n"
        f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    # file:line + bogus_label must both appear in stderr.
    assert str(file_path) in result.stderr, (
        f"stderr must reference the offending file {file_path}; got:\n{result.stderr}"
    )
    assert "bogus_label" in result.stderr, (
        f"stderr must name the bogus label; got:\n{result.stderr}"
    )
    # Must surface a line number — the call is on line 2 of metrics.py.
    line_pattern = re.compile(rf"{re.escape(str(file_path))}:(\d+):")
    match = line_pattern.search(result.stderr)
    assert match is not None, (
        f"stderr must include '<file>:<line>:' for the offending call; "
        f"got:\n{result.stderr}"
    )
    assert int(match.group(1)) >= 1, "line number must be a positive integer"


def test_bad_label_keyword_form_also_exits_one(tmp_path: Path) -> None:
    """The kwarg form ``labelnames=(...)`` must also be checked."""
    _write_counter_file(
        tmp_path,
        counter_call='Counter("foo", "doc", labelnames=("bogus_label",))',
        filename="bad_kwarg.py",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 1, (
        f"expected exit 1 for kwarg-form bogus label; "
        f"got exit={result.returncode}\nstderr:\n{result.stderr}"
    )
    assert "bogus_label" in result.stderr


# ---------------------------------------------------------------------------
# 2. Valid KNOWN_LABELS usage → exit 0
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "label_name",
    [
        "tool_status",
        "tool_name",
        "decision",
        "domain",
        "style_result",
        "render_escaped",
    ],
)
def test_known_label_passes(tmp_path: Path, label_name: str) -> None:
    """Every label in _KNOWN_LABELS is accepted (positional + kwarg)."""
    for form in (
        f'Counter("foo_total", "doc", ("{label_name}",))',
        f'Counter("foo_total", "doc", labelnames=("{label_name}",))',
    ):
        sub = tmp_path / label_name
        sub.mkdir(exist_ok=True)
        _write_counter_file(sub, counter_call=form, filename="metrics.py")
    result = _run_script(tmp_path)
    assert result.returncode == 0, (
        f"expected exit 0 for known label {label_name!r}; "
        f"got exit={result.returncode}\nstderr:\n{result.stderr}"
    )
    assert "pass cardinality check" in result.stdout, (
        f"stdout must announce clean pass; got:\n{result.stdout}"
    )


# ---------------------------------------------------------------------------
# 3. PromQL metric-name regex
# ---------------------------------------------------------------------------


def test_promql_metric_name_good_passes(tmp_path: Path) -> None:
    """A metric name matching ``[a-zA-Z_:][a-zA-Z0-9_:]*`` is accepted."""
    _write_counter_file(
        tmp_path,
        counter_call='Counter("good_metric_2", "doc")',
        filename="good_name.py",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 0, (
        f"PromQL-compliant name should pass; got exit={result.returncode}\n"
        f"stderr:\n{result.stderr}"
    )


def test_promql_metric_name_dash_fails(tmp_path: Path) -> None:
    """A metric name containing a dash violates PromQL and exits 1."""
    file_path = _write_counter_file(
        tmp_path,
        counter_call='Counter("bad-metric", "doc")',
        filename="bad_name.py",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 1, (
        f"PromQL-violating name should fail; got exit={result.returncode}\n"
        f"stderr:\n{result.stderr}"
    )
    assert str(file_path) in result.stderr
    assert "bad-metric" in result.stderr, (
        f"stderr must name the offending metric; got:\n{result.stderr}"
    )


def test_promql_metric_name_digit_prefix_fails(tmp_path: Path) -> None:
    """A metric name starting with a digit violates PromQL and exits 1."""
    _write_counter_file(
        tmp_path,
        counter_call='Counter("2foo", "doc")',
        filename="bad_prefix.py",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 1, (
        f"digit-prefixed metric name should fail; "
        f"got exit={result.returncode}\nstderr:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 4. AST extraction is positional-agnostic
# ---------------------------------------------------------------------------


def test_keyword_only_call_is_extracted(tmp_path: Path) -> None:
    """All-kwargs call ``Counter(name=..., documentation=..., labelnames=...)``.

    Verifies that the AST visitor handles ``Counter(name=...)`` /
    ``Counter(documentation=...)`` / ``Counter(labelnames=...)`` keyword
    forms (in any order) without positional indexing.
    """
    _write_counter_file(
        tmp_path,
        counter_call='Counter(name="foo_total", documentation="doc", labelnames=("bogus_label",))',
        filename="kwargs_only.py",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 1, (
        f"all-kwargs call with bogus label should fail; "
        f"got exit={result.returncode}\nstderr:\n{result.stderr}"
    )
    assert "bogus_label" in result.stderr


# ---------------------------------------------------------------------------
# 5. Non-Counter calls are ignored
# ---------------------------------------------------------------------------


def test_non_counter_call_is_ignored(tmp_path: Path) -> None:
    """A non-Counter function with label-like string args must not be flagged.

    The AST visitor walks for ``Counter`` specifically; ``some_other_func``
    with the same label-shaped args MUST NOT trigger a violation.
    """
    file_path = tmp_path / "not_counter.py"
    file_path.write_text(
        "def some_other_func(*args: str) -> None:\n"
        "    pass\n"
        'some_other_func("label1", "label2")\n',
        encoding="utf-8",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 0, (
        f"non-Counter calls must not be flagged; got exit={result.returncode}\n"
        f"stderr:\n{result.stderr}"
    )
    assert "label1" not in result.stderr, (
        f"stderr must not mention non-Counter args; got:\n{result.stderr}"
    )
    assert "label2" not in result.stderr


def test_counter_class_definition_is_not_a_call(tmp_path: Path) -> None:
    """Subclassing ``Counter`` is not the same as instantiating it.

    The visitor only matches ``Call`` nodes (function invocations), so a
    ``class Foo(Counter): pass`` definition is correctly skipped.
    """
    (tmp_path / "subclass.py").write_text(
        "from fastblocks.observability.counters import Counter\n"
        "class MyCounter(Counter):\n"
        "    pass\n",
        encoding="utf-8",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 0, (
        f"Counter subclass definition must not be flagged; "
        f"got exit={result.returncode}\nstderr:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 6. Skipping non-source paths
# ---------------------------------------------------------------------------


def test_pycache_and_venv_are_skipped(tmp_path: Path) -> None:
    """Files under __pycache__/.venv are not walked.

    Even if a file in those locations would otherwise violate, the
    walker MUST skip it so vendored / cached files never trip CI.
    """
    pycache = tmp_path / "__pycache__"
    pycache.mkdir()
    (pycache / "junk.py").write_text(
        "from fastblocks.observability.counters import Counter\n"
        'Counter("bad-metric", "doc", ("bogus_label",))\n',
        encoding="utf-8",
    )
    venv = tmp_path / ".venv"
    venv.mkdir()
    (venv / "lib.py").write_text(
        "from fastblocks.observability.counters import Counter\n"
        'Counter("bad-metric", "doc", ("bogus_label",))\n',
        encoding="utf-8",
    )
    result = _run_script(tmp_path)
    assert result.returncode == 0, (
        f"__pycache__ and .venv must be skipped; "
        f"got exit={result.returncode}\nstderr:\n{result.stderr}"
    )


# ---------------------------------------------------------------------------
# 7. CLI surface — argv parsing
# ---------------------------------------------------------------------------


def test_no_args_uses_repo_root_default(tmp_path: Path) -> None:
    """Without arguments, the script walks the current directory.

    Verifies the script can be invoked without arguments when the CWD
    contains no violating files.
    """
    import os

    (tmp_path / "clean.py").write_text(
        "x = 1\n",
        encoding="utf-8",
    )
    env = os.environ.copy()
    existing_pythonpath = env.get("PYTHONPATH", "")
    env["PYTHONPATH"] = (
        f"{REPO_ROOT}{os.pathsep}{existing_pythonpath}"
        if existing_pythonpath
        else str(REPO_ROOT)
    )
    result = subprocess.run(
        [sys.executable, "-m", SCRIPT_MODULE],
        capture_output=True,
        text=True,
        check=False,
        cwd=tmp_path,
        env=env,
    )
    assert result.returncode == 0, (
        f"no-arg invocation should pass on clean dir; "
        f"got exit={result.returncode}\nstderr:\n{result.stderr}"
    )


def test_exit_code_on_violation_is_one(tmp_path: Path) -> None:
    """Lock the exit code contract: violations → 1, clean → 0."""
    _write_counter_file(
        tmp_path,
        counter_call='Counter("bad-metric", "doc", ("bogus_label",))',
    )
    result = _run_script(tmp_path)
    assert result.returncode == 1

    clean = tmp_path / "clean"
    clean.mkdir()
    _write_counter_file(
        clean,
        counter_call='Counter("good_total", "doc")',
        filename="metrics.py",
    )
    result = _run_script(clean)
    assert result.returncode == 0


__all__ = [
    "REPO_ROOT",
    "SCRIPT_MODULE",
]
