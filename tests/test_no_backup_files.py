"""D0 + D9: ensure no .backup files leak into the repo and the
docs-vs-code audit gates hold.

D0 was added by Task 1 — backup files were left over from the
Phase 1A style adapter migration; CI catches them if a future
migration reintroduces them.

D9 was added by Task 10 — the lychee link checker and the
aspirational-claims file must be present and clean.

If a future change adds a backup file, removes the claim-gap
file, or breaks an internal markdown link, CI catches it.
"""
from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".crackerjack", "node_modules", ".venv", ".tox", "build", "dist"}


def _iter_paths() -> Path:
    """Yield every file under REPO_ROOT that is not in an excluded dir."""
    for p in REPO_ROOT.rglob("*"):
        if any(part in EXCLUDED_DIRS for part in p.parts):
            continue
        if p.is_file():
            yield p


def test_no_backup_files_in_repo():
    backup_files = [
        p.relative_to(REPO_ROOT).as_posix()
        for p in _iter_paths()
        if p.name.endswith(".backup") or p.name.endswith(".backup.json")
    ]
    assert not backup_files, (
        f"D0: backup files leaked into repo: {backup_files}. "
        f"Remove them or extend EXCLUDED_DIRS."
    )


@pytest.mark.parametrize("subdir", ["archive", "docs/archive"])
def test_archive_directory_has_readme(subdir: str):
    readme = REPO_ROOT / subdir / "README.md"
    assert readme.exists(), f"D0: {readme} missing; archive contents must be documented"


# ---------------------------------------------------------------------------
# D9: docs-vs-code audit gates
# ---------------------------------------------------------------------------


LYCHEE_TIMEOUT_SECONDS = 120


@pytest.fixture(scope="module")
def lychee_path() -> str:
    """Locate a runnable ``lychee`` binary on PATH.

    Skips the test if no binary is available — this lets the suite
    run in environments that don't ship lychee (e.g. minimal CI
    runners) without failing the gate for reasons unrelated to
    the docs audit.
    """
    path = shutil.which("lychee")
    if path is None:
        pytest.skip("lychee not installed on PATH")
    return path


def test_lychee_finds_no_broken_internal_links(lychee_path: str):
    """Run lychee in offline mode over every Markdown file.

    Asserts there are no broken internal links. External links are
    skipped by ``--offline`` so this gate is hermetic.
    """
    proc = subprocess.run(
        [lychee_path, "--offline", "--no-progress", "**/*.md"],
        cwd=REPO_ROOT,
        capture_output=True,
        text=True,
        timeout=LYCHEE_TIMEOUT_SECONDS,
    )
    assert proc.returncode == 0, (
        f"D9: lychee reported broken links.\n"
        f"stdout:\n{proc.stdout}\nstderr:\n{proc.stderr}"
    )


def test_known_claim_gaps_file_present():
    """``docs/known-claim-gaps.md`` must exist with the documented
    table header. The header is the gate: any future file reformat
    that drops the header breaks this assertion.
    """
    path = REPO_ROOT / "docs" / "known-claim-gaps.md"
    assert path.exists(), (
        f"D9: {path} missing; aspirational README claims must be "
        f"documented here per docs/known-claim-gaps.md spec."
    )
    content = path.read_text(encoding="utf-8")
    for header in ("# Known Claim Gaps", "| Claim |", "|---|---|---|---|"):
        assert header in content, (
            f"D9: {path} missing required header fragment {header!r}"
        )


def test_adapter_docs_coverage():
    """Every in-scope adapter module (templates, style, icons, fonts)
    must have a matching ``docs/adapters/<name>.md`` file.
    """
    expected = ["templates.md", "style.md", "icons.md", "fonts.md"]
    adapters_dir = REPO_ROOT / "docs" / "adapters"
    missing = [name for name in expected if not (adapters_dir / name).exists()]
    assert not missing, (
        f"D9: missing adapter docs in {adapters_dir}: {missing}. "
        f"Create stubs (see docs/adapters/README.md index)."
    )
