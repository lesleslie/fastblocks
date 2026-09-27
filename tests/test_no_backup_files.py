"""D0: ensure no .backup files leak into the repo.

CI fails if any backup file exists under fastblocks/. Backup files
were left over from the Phase 1A style adapter migration; D0 purges
them. If a future migration introduces a backup file, CI catches it.
"""
from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[1]
EXCLUDED_DIRS = {".git", ".crackerjack", "node_modules", ".venv", ".tox", "build", "dist"}


def _iter_paths():
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