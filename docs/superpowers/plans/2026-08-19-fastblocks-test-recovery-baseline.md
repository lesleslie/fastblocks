# FastBlocks Recovery Baseline

- HEAD: 99ff1fd34478ee031989d1eed1116cf01e84c877
- WIP entries: 94 (91 modified tracked, 3 untracked)
- Initial counts: 1695 collected, 1553 passed, 117 failed, 21 skipped, 4 xpassed, 301 warnings
- Canonical command (read-only; recovery worktree has no `.venv`; do NOT install, sync, or create a symlink): `PYTHONPATH=. PYTHONDONTWRITEBYTECODE=1 /Users/les/Projects/fastblocks/.venv/bin/pytest --no-cov -p no:cacheprovider -o addopts='' --tb=short -q`
- Downstream execution contract: all later tasks must run this exact command from the recovery worktree rooted at `/Users/les/.claude/worktrees/fastblocks-test-recovery-2026-08-19`; do NOT run `.venv/bin/pytest` from the recovery worktree (its `.venv` lives in the original `/Users/les/Projects/fastblocks` checkout); do NOT `uv sync`, do NOT `uv pip install`, do NOT symlink `.venv`; the test environment is read-only by design.
- Anchor SHA: `99ff1fd34478ee031989d1eed1116cf01e84c877` (actual recovery HEAD); later task briefs and recovery execution MUST anchor this SHA; do NOT re-anchor to the pre-plan SHA `4a9fab62bc654c7b31054d24c90c2e8a41f56310`.
- Shared ownership lock: initializers.py, main.py, direct dependency tests = one owner
- Notes: later diagnosis found possible rendering collection issue; verify it explicitly.
