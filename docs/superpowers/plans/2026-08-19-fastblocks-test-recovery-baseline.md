# FastBlocks Recovery Baseline

- HEAD: 99ff1fd34478ee031989d1eed1116cf01e84c877
- WIP entries: 94 (91 modified tracked, 3 untracked)
- Initial counts: 1695 collected, 1553 passed, 117 failed, 21 skipped, 4 xpassed, 301 warnings
- Canonical command: PYTHONDONTWRITEBYTECODE=1 .venv/bin/pytest --no-cov -p no:cacheprovider -o addopts='' --tb=short -q
- Shared ownership lock: initializers.py, main.py, direct dependency tests = one owner
- Notes: later diagnosis found possible rendering collection issue; verify it explicitly.