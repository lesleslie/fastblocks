"""A11y test collection gating.

Per Phase 1.5 spec Task 7: use pytest_ignore_collect (matches project
pattern at tests/adapters/templates/conftest.py) to skip a11y subtree
when Playwright browser binary is missing.

WHY pytest_ignore_collect (not pytest.importorskip): axe-playwright-python
and playwright ARE in dev deps (pyproject.toml:77, 82) so they're
installed. The actual failure mode is Playwright browser binary missing.

Deferred to Phase 1.5+ or Phase 2: actual browser install.
"""
from __future__ import annotations

import shutil
from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config):
    """Skip a11y subtree if no Playwright-compatible browser is available."""
    # Only act on the a11y subtree
    if "tests/a11y" not in str(collection_path):
        return False

    # Probe for a browser binary
    browser_paths = [
        shutil.which("chromium"),
        shutil.which("chromium-browser"),
        shutil.which("google-chrome"),
        shutil.which("msedge"),
    ]
    if any(browser_paths):
        return False  # browser available; collect normally

    # Try playwright's own probe
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            p.chromium.launch().close()
        return False  # playwright can launch; collect normally
    except Exception:
        return True  # browser missing; skip this subtree
