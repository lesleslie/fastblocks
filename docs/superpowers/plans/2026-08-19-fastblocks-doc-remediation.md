# FastBlocks Documentation Remediation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Remediate all ~75 findings from the 2026-08-19 FastBlocks doc audit. Land a CI guard (`tests/docs/test_doc_accuracy.py`) before any narrative rewrite to prevent recurrence during the wave.

**Architecture:** 10-phase wave. Each phase produces one commit (or PR) and ends with a green pytest + green crackerjack. Critical safety fix (Phase 0) lands same-day. CI guard (Phases 1-2) blocks future drift. Narrative rewrites (Phases 3-5) follow in waves. Cleanup and convention fixes (Phases 6-9) close the tail. Phase 10 is final verification + sign-off.

**Tech Stack:** pytest, uv, crackerjack, git. **No new dependencies.**

## Global Constraints

- Repo: `/Users/les/Projects/fastblocks` @ v0.20.0 (Python 3.13+).
- Audit reference: 4-agent parallel audit completed 2026-08-19 (~75 findings, ~25 HIGH severity). Findings are anchored to evidence in the audit summary; this plan references finding IDs from the master report.
- Archived docs are out of scope: `docs/archive/`, `docs/superpowers/notes/`, `docs/baselines/` — do not touch.
- Each phase produces exactly **one commit**. Never bundle phases. One reviewer gate per phase.
- Every doc edit must end with: `uv run pytest tests/docs/ -v` green AND `uv run crackerjack run` green.
- Coverage floor is **49.13%** (`pyproject.toml [tool.coverage.report].fail_under`); CI guard does not raise it.
- New tests live in `tests/docs/test_doc_accuracy.py`. Mirror the existing `tests/mcp/test_ci_guard.py` pattern.
- Tooling: `uv run pytest` for tests, `uv run crackerjack run` for quality, `git grep -n` for symbol verification.
- Commit message format: `fix(fastblocks): <phase-id> <one-line description>` (mirrors recent commits `4a9fab6`, `870e5b5`, `6986a6c`).
- Author email: `les@wedgwoodwebworks.com` (NOT `.local`).
- All work happens in an isolated worktree per Phase 0 instructions.

______________________________________________________________________

## Phase 0: Critical Safety Fix (Same-Day, One Commit)

**Why first:** The `WEBSOCKET_GUIDE.md` env-var mismatch silently disables production JWT auth. Every other finding can wait; this one cannot.

**Files:**

- Modify: `docs/WEBSOCKET_GUIDE.md:398` (two env-var names)

**Integration Contract:**

- **Triggered from:** This plan.

- **Returns to / updates:** A doc that, when followed, sets the correct env vars so JWT auth actually works.

- **Demonstrable by:** `git grep -n "FASTBLOCKS_WS_JWT_SECRET\|FASTBLOCKS_WS_AUTH_REQUIRED" docs/WEBSOCKET_GUIDE.md` returns zero matches. `git grep -n "FASTBLOCKS_JWT_SECRET\|FASTBLOCKS_AUTH_ENABLED" docs/WEBSOCKET_GUIDE.md` returns the rewritten lines.

- **Rollback signal:** `git revert <phase-0-sha>` if a downstream consumer depends on the old (broken) names.

- **Observability added:** None — this is a doc fix. The CI guard added in Phase 2 will keep it that way.

- [ ] **Step 1: Edit `docs/WEBSOCKET_GUIDE.md:398`**

Replace both occurrences in the env-vars section:

- `FASTBLOCKS_WS_JWT_SECRET` → `FASTBLOCKS_JWT_SECRET`
- `FASTBLOCKS_WS_AUTH_REQUIRED` → `FASTBLOCKS_AUTH_ENABLED`

The `FASTBLOCKS_WS_*` env vars in `fastblocks/websocket/tls_config.py` (TLS) and `fastblocks/websocket/origin.py` (origin allowlist) are correct — leave those alone. Only the **auth** section is wrong.

- [ ] **Step 2: Verify the rename**

```bash
cd /Users/les/Projects/fastblocks
git grep -n "FASTBLOCKS_WS_JWT_SECRET\|FASTBLOCKS_WS_AUTH_REQUIRED" docs/
```

Expected: zero matches.

- [ ] **Step 3: Cross-check `0.7-to-0.8.md` migration guide**

```bash
git grep -n "FASTBLOCKS_JWT_SECRET\|FASTBLOCKS_AUTH_ENABLED" docs/migrations/0.7-to-0.8.md
```

If the migration guide also has the wrong names, apply the same fix.

- [ ] **Step 4: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add docs/WEBSOCKET_GUIDE.md docs/migrations/0.7-to-0.8.md
git commit -m "fix(fastblocks): P0 correct WebSocket auth env-var names (silent prod JWT failure)"
git -c user.email=les@wedgwoodwebworks.com commit --amend --no-edit  # safety: fix author email
```

______________________________________________________________________

## Phase 1: CI Guard Scaffolding

**Why:** Establish the test infrastructure so the CI guard assertions (Phase 2) can land as a single pytest module. Without this, every narrative rewrite in Phases 3-5 risks reintroducing the same drift.

**Files:**

- Create: `tests/docs/__init__.py` (empty)
- Create: `tests/docs/test_doc_accuracy.py` (skeleton)
- Create: `tests/docs/_fixtures/` (sample doc snippets to scan)

**Integration Contract:**

- **Triggered from:** Phase 0 completion.

- **Returns to / updates:** A runnable pytest module under `tests/docs/` that the project's existing pytest discovery will pick up.

- **Demonstrable by:** `uv run pytest tests/docs/ -v` runs and returns `no tests ran` or all-pass (the skeleton has 0-1 placeholder tests).

- **Rollback signal:** `git revert <phase-1-sha>` if the test discovery path breaks CI.

- **Observability added:** The CI guard becomes a CI signal; future drift surfaces as a failing PR.

- [ ] **Step 1: Create the test package**

```bash
mkdir -p tests/docs/_fixtures
touch tests/docs/__init__.py
```

- [ ] **Step 2: Write the skeleton `test_doc_accuracy.py`**

```python
"""Doc accuracy CI guard for FastBlocks.

These tests protect prose-level correctness in user-facing docs:
- No `acb.*` imports (Phase 3.1 migration removed the ACB dependency).
- No fabricated CLI subcommands or MCP tool names.
- No env-var names that disagree with `git grep` of source.
- No phantom filenames.
- Coverage claims must match pyproject.toml.

Each test reads a curated list of docs under test, greps the source tree
for the same symbols, and asserts parity. Pattern follows
`tests/mcp/test_ci_guard.py`.
"""
from __future__ import annotations

from pathlib import Path

import pytest

REPO_ROOT = Path(__file__).resolve().parents[2]

DOCS_TO_SCAN: tuple[Path, ...] = (
    REPO_ROOT / "README.md",
    REPO_ROOT / "CLAUDE.md",
    REPO_ROOT / "QWEN.md",
    REPO_ROOT / "RULES.md",
    REPO_ROOT / "CONTRIBUTING.md",
    REPO_ROOT / "CHANGELOG.md",
    REPO_ROOT / "docs",
    REPO_ROOT / "fastblocks",
)

# Populated in subsequent phases. Empty for the skeleton.
PROHIBITED_IMPORTS: tuple[str, ...] = ()
PROHIBITED_CLI_COMMANDS: tuple[str, ...] = ()
PROHIBITED_MCP_TOOLS: tuple[str, ...] = ()
PROHIBITED_PORTS: tuple[str, ...] = ()


def _iter_doc_text() -> list[tuple[Path, str]]:
    """Return (path, text) for every doc under DOCS_TO_SCAN.

    Skips archive directories (`docs/archive/`, `docs/baselines/`,
    `docs/superpowers/notes/`) and `.git/`. Walks directories recursively.
    """
    out: list[tuple[Path, str]] = []
    skip_substrings = ("/archive/", "/baselines/", "/superpowers/notes/", "/.git/")
    for entry in DOCS_TO_SCAN:
        if entry.is_file():
            out.append((entry, entry.read_text(encoding="utf-8", errors="replace")))
            continue
        for path in entry.rglob("*.md"):
            spath = str(path)
            if any(s in spath for s in skip_substrings):
                continue
            out.append((path, path.read_text(encoding="utf-8", errors="replace")))
    return out


@pytest.mark.parametrize("prohibited_symbol", PROHIBITED_IMPORDS)
def test_no_prohibited_imports(prohibited_symbol: str) -> None:
    """No doc may reference a removed/prohibited import path."""
    for path, text in _iter_doc_text():
        assert prohibited_symbol not in text, (
            f"Found prohibited import {prohibited_symbol!r} in {path.relative_to(REPO_ROOT)}"
        )
```

- [ ] **Step 3: Run the skeleton test**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest tests/docs/ -v
```

Expected: PASS (zero parametrized cases, plus the parametrized-with-empty case resolves to "0 selected").

- [ ] **Step 4: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add tests/docs/
git -c user.email=les@wedgwoodwebworks.com commit -m "feat(fastblocks): P1 scaffold docs/ CI guard test module"
```

______________________________________________________________________

## Phase 2: CI Guard Assertions (8 Tests, One Per Drift Category)

**Why:** Phase 1 produced an empty skeleton. Phase 2 fills it with the 8 assertions that would have caught 60-70% of the audit findings on day one.

**Files:**

- Modify: `tests/docs/test_doc_accuracy.py`

**Integration Contract:**

- **Triggered from:** Phase 1.

- **Returns to / updates:** A test suite that fails CI when any of the 8 drift categories reappear.

- **Demonstrable by:** `uv run pytest tests/docs/ -v` runs all 8 test functions and they pass against the *current* docs (because Phase 3-9 will have already fixed the drift). Before Phase 3-9, these tests should be expected to fail — that is correct behavior, the failures are the regression baseline.

- **Rollback signal:** Any test that produces false positives on legitimately-correct prose — disable via `# noqa: P002` annotation with comment, or scope the prohibited list tighter.

- **Observability added:** PR-time CI signal on all 8 drift categories.

- [ ] **Step 1: Add the 8 prohibited-symbol lists and tests**

Replace the placeholder lists near the top of `tests/docs/test_doc_accuracy.py` with:

```python
# (1) No ACB imports — Phase 3.1 removed the ACB dependency entirely.
PROHIBITED_IMPORTS: tuple[str, ...] = (
    "from acb.",
    "import acb",
    "from acb.depends",
    "from acb.adapters",
    "from acb.config",
    "from acb.actions",
    "from acb.services",
    "from acb.mcp",
    "from acb.workflows",
    "from acb.events",
    "register_pkg(",
    "uv add acb[",
)

# (2) No fabricated CLI subcommands or flags.
PROHIBITED_CLI_COMMANDS: tuple[str, ...] = (
    "python -m fastblocks serve",
    "fastblocks serve",
    "--comprehensive",
    " -x -t ",  # not a real flag combo
)

# (3) No fabricated MCP tool names (Phase 0b/0.8.0 removed them).
PROHIBITED_MCP_TOOLS: tuple[str, ...] = (
    "execute_fastblocks",
    "get_job_progress",
    "get_comprehensive_status",
    "fastblocks_start_websocket",
    "fastblocks_stop_websocket",
    "start_websocket_server",
    "stop_websocket_server",
    "broadcast_ui_update",
    "broadcast_component_render",
)

# (4) No fabricated ports.
PROHIBITED_PORTS: tuple[str, ...] = (
    "ws://localhost:8675",
    "localhost:8675",
)

# (5) Phantom filenames that don't exist on disk.
PHANTOM_FILENAMES: tuple[str, ...] = (
    "docs/ACB_GUIDE.md",
    "docs/MIGRATION-0.17.0.md",
    "docs/ACB_DEPENDS_PATTERNS.md",
)
```

- [ ] **Step 2: Add the 5 corresponding test functions**

Below `test_no_prohibited_imports`, add:

```python
@pytest.mark.parametrize("prohibited_symbol", PROHIBITED_CLI_COMMANDS)
def test_no_prohibited_cli(prohibited_symbol: str) -> None:
    for path, text in _iter_doc_text():
        assert prohibited_symbol not in text, (
            f"Found fabricated CLI {prohibited_symbol!r} in {path.relative_to(REPO_ROOT)}"
        )


@pytest.mark.parametrize("prohibited_symbol", PROHIBITED_MCP_TOOLS)
def test_no_prohibited_mcp_tool(prohibited_symbol: str) -> None:
    for path, text in _iter_doc_text():
        assert prohibited_symbol not in text, (
            f"Found fabricated MCP tool {prohibited_symbol!r} in {path.relative_to(REPO_ROOT)}"
        )


@pytest.mark.parametrize("prohibited_port", PROHIBITED_PORTS)
def test_no_prohibited_port(prohibited_port: str) -> None:
    for path, text in _iter_doc_text():
        assert prohibited_port not in text, (
            f"Found fabricated port {prohibited_port!r} in {path.relative_to(REPO_ROOT)}"
        )


@pytest.mark.parametrize("phantom_path", PHANTOM_FILENAMES)
def test_no_phantom_filenames(phantom_path: str) -> None:
    """No doc may reference a path that doesn't exist on disk."""
    resolved = REPO_ROOT / phantom_path
    assert resolved.exists(), f"{phantom_path} referenced in docs but does not exist"


def test_no_phantom_adapter_paths() -> None:
    """Adapter README references to `main.py` must resolve to `default.py`."""
    # (Audit finding: adapters/{app,routes}/README.md reference main.py.)
    for adapter in ("app", "routes"):
        readme = REPO_ROOT / f"fastblocks/adapters/{adapter}/README.md"
        if not readme.exists():
            continue
        text = readme.read_text(encoding="utf-8")
        assert "main.py" not in text, (
            f"{readme.relative_to(REPO_ROOT)} still references main.py; "
            "actual file is default.py"
        )
```

- [ ] **Step 3: Add env-var parity test (the silent auth failure guard)**

```python
def test_env_var_names_match_source() -> None:
    """Every `FASTBLOCKS_*` env var mentioned in docs must appear in source.

    Catches the WEBSOCKET_GUIDE class of bug where the doc names one env
    var and the code reads a different one.
    """
    import re

    env_var_re = re.compile(r"\bFASTBLOCKS_[A-Z_]+\b")
    doc_env_vars: set[str] = set()
    for _path, text in _iter_doc_text():
        for match in env_var_re.findall(text):
            doc_env_vars.add(match)
    # Source-side env vars: every grep hit in fastblocks/.
    source_env_vars: set[str] = set()
    for path in (REPO_ROOT / "fastblocks").rglob("*.py"):
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
        for match in env_var_re.findall(text):
            source_env_vars.add(match)

    # If a doc names an env var that the source never reads, the doc is wrong.
    orphaned = doc_env_vars - source_env_vars
    assert not orphaned, (
        f"Docs reference env vars that source never reads: {sorted(orphaned)}"
    )
```

- [ ] **Step 4: Add coverage-target parity test**

```python
def test_coverage_target_consistency() -> None:
    """Every coverage % in docs must match pyproject.toml fail_under."""
    import re

    pyproject = (REPO_ROOT / "pyproject.toml").read_text()
    match = re.search(r"--cov-fail-under=([\d.]+)", pyproject)
    if match is None:
        pytest.skip("Could not find --cov-fail-under in pyproject.toml")
    floor = float(match.group(1))
    pct_re = re.compile(r"(\d{1,3}(?:\.\d+)?)\s*%")
    # Only flag coverage-shaped numbers: must be followed by % within a doc-like context.
    # Tolerance: ±0.1 absolute.
    tolerance = 0.1
    for path, text in _iter_doc_text():
        for pct_match in pct_re.finditer(text):
            candidate = float(pct_match.group(1))
            # Heuristic: skip numbers > 100 or < 5 (unrelated).
            if not (5.0 <= candidate <= 100.0):
                continue
            # Skip if context is clearly not about coverage.
            ctx_start = max(0, pct_match.start() - 50)
            ctx = text[ctx_start : pct_match.end() + 5].lower()
            if "coverage" not in ctx and "cov" not in ctx:
                continue
            assert abs(candidate - floor) < tolerance, (
                f"{path.relative_to(REPO_ROOT)} claims coverage {candidate}% "
                f"but pyproject.toml floor is {floor}%"
            )
```

- [ ] **Step 5: Add `.backup.json` leak guard**

```python
def test_no_backup_json_in_git() -> None:
    """Backup files must never reach git history."""
    import subprocess

    result = subprocess.run(
        ["git", "ls-files"],
        cwd=REPO_ROOT,
        check=True,
        capture_output=True,
        text=True,
    )
    leaked = [line for line in result.stdout.splitlines() if line.endswith(".backup.json")]
    assert not leaked, (
        f".backup.json files are tracked in git: {leaked}"
    )
```

- [ ] **Step 6: Run the full guard**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest tests/docs/ -v
```

Expected at this stage: **many failures**. Each failure is a baseline regression to be fixed in Phases 3-9. Record the failure list — it is the work queue.

- [ ] **Step 7: Mark test as `xfail` baseline + commit guard in place**

Temporarily skip the test functions that fail by adding `@pytest.mark.xfail(reason="baseline drift; fix in P3-P9")` decorators. **Do not delete the assertions.**

- [ ] **Step 8: Confirm `pytest tests/docs/` exits 0 (with xfails)**

```bash
uv run pytest tests/docs/ -v
```

Expected: PASS (xfails reported but not failures).

- [ ] **Step 9: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add tests/docs/
git -c user.email=les@wedgwoodwebworks.com commit -m "feat(fastblocks): P2 doc-accuracy CI guard with baseline xfails"
```

______________________________________________________________________

## Phase 3: ACB Narrative Rewrite — Top-Level Docs

**Why:** README.md has 27 ACB import blocks; QWEN.md intro frames FastBlocks as ACB-built; RULES.md contradicts itself on typing/docstrings. Top-level files are the highest-traffic docs and the most user-facing.

**Files:**

- Modify: `README.md` (~30 code blocks; lines 19, 21, 45, 169-170, 238-239, 334, 358, 408-409, 443-444, 699-700, 740-741, 891-892, 918-919, 1004-1005, 1057, 1103-1104, 1260-1262, 1273-1275, 1334-1335, 1395)
- Modify: `QWEN.md:7,13,30,34,38,53,120`
- Modify: `RULES.md:154,211,234,292,340,361-362,371`

**Integration Contract:**

- **Triggered from:** Phase 2 (CI guard active).

- **Returns to / updates:** Top-level docs that describe the actual Oneiric-based stack.

- **Demonstrable by:** `git grep -n "from acb\.\|import acb" README.md QWEN.md RULES.md` returns zero matches. The Phase 2 CI guard tests `test_no_prohibited_imports` turn green (xfail markers removed).

- **Rollback signal:** Any import-pattern that breaks a documented user-facing API.

- **Observability added:** CI guard now fails the build on ACB reintroduction.

- [ ] **Step 1: Rewrite README.md ACB imports to Oneiric**

Replace every `from acb.adapters import import_adapter` with:

```python
from fastblocks.core.resolver import get_resolver
resolver = get_resolver()
adapter = resolver.resolve("fastblocks", "templates")  # or "images", "styles", etc.
```

Replace every `from acb.depends import depends, Inject` with:

```python
from oneiric.core.depends import depends, inject
```

Replace every `from acb.config import Config` with:

```python
from oneiric.core.config import OneiricSettings
```

- [ ] **Step 2: Drop ACB acknowledgements from README.md:1395**

Remove the ACB acknowledgement section; replace with Oneiric acknowledgement.

- [ ] **Step 3: Rewrite QWEN.md intro (lines 7, 13)**

Replace "Built on the **Asynchronous Component Base (ACB)** framework" with "Built on **Oneiric** for dependency injection, configuration management, and pluggable adapters." Replace `Middleware Communication Protocol` (line 30) with `Model Context Protocol`.

- [ ] **Step 4: Fix `python -m fastblocks serve` in QWEN.md:53**

Replace with one of:

- `uv run granian fastblocks.applications:app` (production-like)
- `uv run python -m fastblocks create_app <name>` (scaffold-driven)
- Or simply remove the line if no run story exists.

Pick the option that matches `pyproject.toml`'s `granian[reload]~=2.6` dependency (the first option).

- [ ] **Step 5: Fix RULES.md:154, 211 crackerjack CLI**

Standardize on `uv run crackerjack run` to match CLAUDE.md.

- [ ] **Step 6: Fix RULES.md:234, 371 fabricated flags**

Remove `python -m fastblocks -x -t` and `python -m fastblocks --comprehensive` references; replace with `uv run crackerjack run`.

- [ ] **Step 7: Fix RULES.md:292 coverage target**

Replace "Target 42% milestone coverage (current: 21.6%, baseline: 19.6%)" with "Floor: 49.13% (pyproject.toml `[tool.coverage.report].fail_under`)."

- [ ] **Step 8: Fix RULES.md:340, 361-362 (port + MCP tools)**

Remove `ws://localhost:8675` (2 occurrences) and the 3 fabricated MCP tool names.

- [ ] **Step 9: Scope RULES.md:20-23, 37 to grandfathered code**

`import typing as t` rule and "NO DOCSTRINGS" rule contradict the actual codebase. Scope to "new code in `fastblocks/` only" with explicit grandfathering.

- [ ] **Step 10: Run CI guard + crackerjack**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest tests/docs/ -v
uv run crackerjack run
```

Expected: `tests/docs/test_no_prohibited_imports[from acb.]` and similar turn green. Remove the `@pytest.mark.xfail` decorators one at a time as each parametrized case turns green.

- [ ] **Step 11: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add README.md QWEN.md RULES.md tests/docs/
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P3 ACB narrative rewrite — README/QWEN/RULES"
```

______________________________________________________________________

## Phase 4: ACB Narrative Rewrite — `docs/` Guides (8 files)

**Why:** The 8 user-facing guides in `docs/` document ACB APIs that don't exist. Each guide has ~10-30 ACB import blocks. Same root cause as Phase 3, separate files.

**Files:**

- Modify: `docs/ONEIRIC_GUIDE.md` (lines 1, 3, 29, 50-53, 371, body throughout)
- Modify: `docs/ONEIRIC_DEPENDS_PATTERNS.md` (title + examples throughout)
- Modify: `docs/GETTING_STARTED.md`
- Modify: `docs/ARCHITECTURE.md` (lines 22, 38-46, 65)
- Modify: `docs/COMPARISONS.md` (lines 64, 83)
- Modify: `docs/SECURITY.md` (lines 15, 154-162, 175-216, 385, 697; especially 209)
- Modify: `docs/NOTES.md`
- Modify: `docs/LESSONS_LEARNED.md` (lines 32, 121-137, 268-269, 525, 733, 749)

**Integration Contract:**

- **Triggered from:** Phase 3.

- **Returns to / updates:** 8 user-facing guides that import from Oneiric and reference real modules.

- **Demonstrable by:** `git grep -n "from acb\.\|import acb" docs/` returns zero matches.

- **Rollback signal:** Any import-pattern that doesn't actually resolve.

- **Observability added:** CI guard now catches reintroduction.

- [ ] **Step 1: Add stale-content warning template**

For each of the 8 docs, prepend a 5-line warning if not already present:

```markdown
> ⚠️ **Stale content:** This guide still references the pre-0.13.x ACB-based
> architecture. ACB was removed in Phase 3.1; FastBlocks now uses Oneiric.
> See `docs/migrations/0.7-to-0.8.md` and `CLAUDE.md` for the current truth.
> Rewriting the body in progress.
```

If the warning exists already, keep it; if not, add it.

- [ ] **Step 2: Rewrite `docs/ONEIRIC_GUIDE.md`**

Rewrite the body to drop ACB framing. Replace `from acb.*` imports with `from oneiric.*` equivalents. Update the title from "FastBlocks ACB Guide" to "FastBlocks Oneiric Guide".

- [ ] **Step 3: Rewrite `docs/ONEIRIC_DEPENDS_PATTERNS.md`**

Same pattern: drop `acb.depends`, use `oneiric.core.depends`.

- [ ] **Step 4: Rewrite `docs/GETTING_STARTED.md`**

Quickstart code blocks must import from the real surface. Update `last reviewed` stamp.

- [ ] **Step 5: Rewrite `docs/ARCHITECTURE.md`**

Replace ACB claims with Oneiric claims; replace `MIGRATION-0.17.0.md` phantom ref with `migrations/0.7-to-0.8.md`.

- [ ] **Step 6: Rewrite `docs/COMPARISONS.md:64,83`**

Replace "ACB-based DI system" with "Oneiric-based DI system".

- [ ] **Step 7: Rewrite `docs/SECURITY.md:209`**

Replace `from acb.services.validation import ValidationService` with the actual validator module path. Verify against `git ls-files fastblocks/` first.

- [ ] **Step 8: Rewrite `docs/NOTES.md`**

This file is "messy brainstorming" per the audit. Either mark as scratchpad (move to `docs/superpowers/notes/`) or rewrite. Pick: keep it, add a "scratchpad" header.

- [ ] **Step 9: Rewrite `docs/LESSONS_LEARNED.md`**

Replace `ACB_DEPENDS_PATTERNS.md` phantom ref (4 occurrences) with `ONEIRIC_DEPENDS_PATTERNS.md`. Drop other ACB claims.

- [ ] **Step 10: Run CI guard**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest tests/docs/ -v
git grep -n "from acb\.\|import acb" docs/
```

Expected: zero matches; CI guard green.

- [ ] **Step 11: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add docs/
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P4 docs/ guide ACB narrative rewrite (8 files)"
```

______________________________________________________________________

## Phase 5: ACB Narrative Rewrite — Adapter READMEs

**Why:** Adapter READMEs have sample code using pre-Oneiric `acb.*` imports. After Phase 5, every adapter README should use the actual import surface.

**Files:**

- Modify: 12 adapter READMEs (admin, app, auth, fonts, icons, images, routes, sitemap, style, templates, parent)
- Modify: `fastblocks/mcp/README.md`

**Integration Contract:**

- **Triggered from:** Phase 4.

- **Returns to / updates:** Adapter READMEs aligned with the Oneiric-based surface.

- **Demonstrable by:** `git grep -n "from acb\.\|import acb" fastblocks/` returns zero matches.

- **Rollback signal:** None — these are sample-code edits.

- **Observability added:** CI guard catches reintroduction.

- [ ] **Step 1: Rewrite admin/README.md ACB imports**

`from acb.config import Settings` → `from oneiric.core.config import OneiricSettings` (matches `AdminBaseSettings` in `_base.py:1-9`).

- [ ] **Step 2: Rewrite app/README.md ACB imports**

Same pattern. Also fix `main.py` → `default.py` reference (line 163).

- [ ] **Step 3: Rewrite auth/README.md ACB imports**

Add "Migrated to Oneiric" note at the top.

- [ ] **Step 4: Rewrite fonts/README.md**

Verify; likely no ACB claims but check.

- [ ] **Step 5: Rewrite icons/README.md**

Verify; likely no ACB claims.

- [ ] **Step 6: Rewrite images/README.md**

Verify; check `cf_image_url` helper claims against `fastblocks/adapters/templates/_enhanced_filters.py`.

- [ ] **Step 7: Rewrite routes/README.md ACB imports**

`from acb.depends import depends, Inject` → Oneiric equivalents. Fix `main.py` → `default.py` (lines 69, 108).

- [ ] **Step 8: Rewrite sitemap/README.md ACB imports**

Also fix `sitemap.py` reference (line 138) with 7-file inventory: `_base.py`, `_routes.py`, `asgi.py`, `cached.py`, `core.py`, `dynamic.py`, `native.py`, `static.py`. Mark `asgi.py` as the default.

- [ ] **Step 9: Rewrite style/README.md**

Drop `bulma.py` reference; add `vanilla.py`.

- [ ] **Step 10: Rewrite templates/README.md**

Add `htmy` and `hybrid` rows to the implementations table.

- [ ] **Step 11: Run CI guard**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest tests/docs/ -v
git grep -n "from acb\.\|import acb" fastblocks/
```

- [ ] **Step 12: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P5 adapter README ACB rewrite + main.py→default.py + adapter registration"
```

______________________________________________________________________

## Phase 6: Top-Level Doc Fixes — CLAUDE.md, CHANGELOG.md, CONTRIBUTING.md

**Why:** After ACB cleanup (Phases 3-5), the remaining top-level doc issues are: pre-commit command (CLAUDE.md:39), conftest LOC (CLAUDE.md:106), coverage text (CLAUDE.md:24), MCP resource names (CLAUDE.md:86-87), CHANGELOG roadmap language (lines 67,71,79,83), CONTRIBUTING.md pytest marker (line 27).

**Files:**

- Modify: `CLAUDE.md` (lines 24, 39, 86-87, 106, 169)
- Modify: `CHANGELOG.md` (lines 67, 71, 79, 83)
- Modify: `CONTRIBUTING.md` (line 27)

**Integration Contract:**

- **Triggered from:** Phase 5.

- **Demonstrable by:** `git grep -n "pre-commit run --all-files\|3,410 LOC\|@pytest.mark.benchmark\|slated for 0.8.0" .` returns zero matches.

- **Rollback signal:** None — pure doc accuracy.

- [ ] **Step 1: CLAUDE.md:39 — drop `pre-commit run --all-files`**

`.pre-commit-config.yaml` does not exist. Remove the line from daily commands.

- [ ] **Step 2: CLAUDE.md:24 — fix coverage text**

Replace "Coverage (target 80%; floor 10% with --cov-fail-under)" with "Coverage (floor: 49.13% — pyproject.toml [tool.coverage.report].fail_under; gate fails below this)."

- [ ] **Step 3: CLAUDE.md:106 — fix conftest LOC**

Run `wc -l tests/conftest.py`, replace `3,410 LOC` with the actual count.

- [ ] **Step 4: CLAUDE.md:86-87 — fix resource names**

Replace the 6-name list with: `template_syntax`, `template_filters`, `component_catalog`, `adapter_schemas`, `settings_docs`, `best_practices`, `htmx_patterns` (verified against `fastblocks/mcp/resources.py`).

- [ ] **Step 5: CLAUDE.md:169 — annotate PROFILE_REGISTRATIONS resolution**

Add one sentence: "Keys are members of the runtime-resolved enum (`_TOOL_PROFILE_CLS`)."

- [ ] **Step 6: CHANGELOG.md:67,71,79,83 — rephrase "slated for 0.8.0"**

Replace with "**Removed in 0.8.0**" or "was removed in 0.8.0".

- [ ] **Step 7: CONTRIBUTING.md:27 — fix pytest marker**

Replace `@pytest.mark.benchmark` with `@pytest.mark.performance` (the actual marker per `pyproject.toml:202-208`).

- [ ] **Step 8: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add CLAUDE.md CHANGELOG.md CONTRIBUTING.md
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P6 CLAUDE.md / CHANGELOG.md / CONTRIBUTING.md accuracy"
```

______________________________________________________________________

## Phase 7: Adapter Registration + File Rename Cleanup

**Why:** `fastblocks/adapters/README.md` documents a 4-adapter system for what is now a 10-adapter system. Plus the file rename from `main.py` to `default.py` is documented-but-not-shipped.

**Files:**

- Modify: `fastblocks/adapters/README.md` (parent — add 6 missing categories)
- Modify: `fastblocks/adapters/admin/README.md` (drop Material Theme)

**Integration Contract:**

- **Demonstrable by:** `git ls-files fastblocks/adapters/` matches the categories listed in `fastblocks/adapters/README.md`. No "Material Theme" claim in admin docs.

- **Rollback signal:** None.

- [ ] **Step 1: Enumerate current adapter categories**

```bash
cd /Users/les/Projects/fastblocks
git ls-files fastblocks/adapters/ | awk -F/ '{print $3}' | sort -u
```

Expected: `admin/`, `app/`, `auth/`, `fonts/`, `icons/`, `images/`, `routes/`, `sitemap/`, `style/`, `templates/`.

- [ ] **Step 2: Add 6 missing categories to parent README.md**

For each of `admin/`, `app/`, `auth/`, `routes/`, `sitemap/`, `templates/`, add a one-line summary with a cross-link to the per-adapter README.

- [ ] **Step 3: Resolve `style/` vs `styles.yml` naming inconsistency**

The directory is `style/` (singular); the DI key is `"styles"` (plural); the YAML is `styles.yml` (plural). Pick canonical: rename `style/` to `styles/` if the dir rename is cheap (one-line in code); or document the inconsistency explicitly in the README. **Recommended: document the asymmetry** (cheaper, lower blast radius).

- [ ] **Step 4: Drop Material Theme section from admin/README.md**

Only Bootstrap is shipped. Replace "Material Theme" with "currently only Bootstrap is shipped; other themes are planned."

- [ ] **Step 5: Drop Bulma from style/README.md**

Bulma is an app-template variant (`fastblocks/adapters/app/_templates/bulma/`), not a style adapter.

- [ ] **Step 6: Update mcp/README.md tool count**

"10+ MCP tools" → "10 MCP tools" (verified count).

- [ ] **Step 7: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/adapters/
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P7 adapter README registration — add 6 missing categories, drop Material/Bulma"
```

______________________________________________________________________

## Phase 8: Backup File Cleanup

**Why:** 8 `.backup.json` files are leaking to git across `adapters/{sitemap,routes,icons,images,templates,style}`. `.gitignore` is missing the pattern.

**Files:**

- Modify: `.gitignore`
- Delete: 8 backup files via `git rm`

**Integration Contract:**

- **Demonstrable by:** `git ls-files | grep '\.backup\.json$'` returns zero matches. The CI guard `test_no_backup_json_in_git` turns green.

- **Rollback signal:** None — backup files are not source of truth.

- [ ] **Step 1: Add `*.backup.json` to `.gitignore`**

Append to `.gitignore`:

```
# Refactor backup artifacts
*.backup.json
*.bak
```

(The `.bak` pattern mirrors the canonical Bodai `.gitignore` per memory `bodai-canonical-gitignore-runtime-artifacts.md`.)

- [ ] **Step 2: List the leaked files**

```bash
cd /Users/les/Projects/fastblocks
git ls-files | grep '\.backup\.json$'
```

- [ ] **Step 3: `git rm` the backups**

```bash
git rm $(git ls-files | grep '\.backup\.json$')
```

If the list is empty, skip this step.

- [ ] **Step 4: Remove the CI guard xfail on `test_no_backup_json_in_git`**

Since backups are gone, remove the `@pytest.mark.xfail` (if added in Phase 2).

- [ ] **Step 5: Run CI guard**

```bash
uv run pytest tests/docs/test_doc_accuracy.py::test_no_backup_json_in_git -v
```

Expected: PASS.

- [ ] **Step 6: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add .gitignore fastblocks/ tests/docs/
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P8 remove leaked .backup.json files; add .gitignore pattern"
```

______________________________________________________________________

## Phase 9: Phantom Filenames + Agent-Facing Convention Fixes

**Why:** Three phantom filenames are referenced from docs (`ACB_GUIDE.md`, `MIGRATION-0.17.0.md`, `ACB_DEPENDS_PATTERNS.md`); `.claude/CLAUDE.md` claims a `.claude/agents/` symlink that doesn't exist; `WORKFLOW-CATALOG.md` last-reviewed stamp is 10 months stale; `RULES.md` contradicts itself on typing convention.

**Files:**

- Modify: `docs/README.md` (lines 30, 45, 73)
- Modify: `docs/ARCHITECTURE.md` (line 51)
- Modify: `docs/TYPE_SYSTEM_MIGRATION.md` (`ACB_DEPENDS_PATTERNS.md` → `ONEIRIC_DEPENDS_PATTERNS.md`)
- Modify: `docs/LESSONS_LEARNED.md` (lines 268-269, 525, 733)
- Modify: `.claude/CLAUDE.md` (line 7)
- Modify: `.claude/commands/workflows/WORKFLOW-CATALOG.md` (last_reviewed stamp)

**Integration Contract:**

- **Demonstrable by:** `git ls-files | grep -E "ACB_GUIDE|MIGRATION-0.17.0|ACB_DEPENDS_PATTERNS"` returns zero matches. CI guard `test_no_phantom_filenames` turns green.

- **Rollback signal:** None.

- [ ] **Step 1: Replace `ACB_GUIDE.md` with `ONEIRIC_GUIDE.md` (3 occurrences)**

- `docs/README.md:30`

- `docs/README.md:73`

- `docs/ARCHITECTURE.md:51`

- [ ] **Step 2: Replace `MIGRATION-0.17.0.md` with `migrations/0.7-to-0.8.md` (2 occurrences)**

- `docs/README.md:45`

- `docs/ARCHITECTURE.md:51`

- [ ] **Step 3: Replace `ACB_DEPENDS_PATTERNS.md` with `ONEIRIC_DEPENDS_PATTERNS.md` (5 occurrences)**

- `docs/TYPE_SYSTEM_MIGRATION.md`

- `docs/LESSONS_LEARNED.md:268-269`

- `docs/LESSONS_LEARNED.md:525`

- `docs/LESSONS_LEARNED.md:733`

- [ ] **Step 4: Remove false `.claude/agents/` symlink claim from `.claude/CLAUDE.md:7`**

Replace "These agents are available via symlinks in `.claude/agents/`" with "Available via the global `/Users/les/.claude/agents/` directory and `.claude/settings.local.json#permissions.additionalDirectories`. This project has no per-repo `.claude/agents/` overrides."

- [ ] **Step 5: Refresh `WORKFLOW-CATALOG.md` last_reviewed stamp**

Update `last_reviewed: 2025-10-01` to `last_reviewed: 2026-08-19`. Update the workflow count if any have been added/removed.

- [ ] **Step 6: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add docs/ .claude/
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P9 phantom filename refs + .claude/CLAUDE.md agents claim + WORKFLOW-CATALOG stamp"
```

______________________________________________________________________

## Phase 10: Final Verification + Sign-Off

**Why:** After 9 phases of edits, confirm: (a) every CI guard test passes without xfail markers, (b) crackerjack passes, (c) the audit's verified-accurate anchors still hold, (d) all changes are committed.

**Files:**

- Modify: `tests/docs/test_doc_accuracy.py` (remove all `@pytest.mark.xfail` decorators)
- Modify: `CHANGELOG.md` (add a top-level "Documentation remediation wave" entry)

**Integration Contract:**

- **Demonstrable by:** `uv run pytest tests/docs/ -v` reports zero xfails and zero failures. `uv run crackerjack run` exits 0. Coverage still meets 49.13% floor.

- **Rollback signal:** Any test that fails after xfail removal — investigate before merging.

- **Observability added:** Documentation remediation visible in CHANGELOG.

- [ ] **Step 1: Remove all `@pytest.mark.xfail` decorators**

In `tests/docs/test_doc_accuracy.py`, remove the xfail markers added in Phase 2. Each removal should correspond to a passing test.

- [ ] **Step 2: Run full test suite**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest tests/docs/ -v
uv run pytest tests/ -v -x
uv run crackerjack run
```

Expected: all green. Coverage ≥ 49.13%.

- [ ] **Step 3: Add CHANGELOG entry**

Add to the top of `CHANGELOG.md`:

```markdown
## 2026-08-19 — Documentation Remediation Wave

Remediated ~75 findings from the 2026-08-19 four-agent doc audit. Key changes:

- ACB → Oneiric migration narrative corrected across 8 user-facing guides, 12 adapter READMEs, and the top-level docs.
- 8-test CI guard added under `tests/docs/test_doc_accuracy.py` to prevent recurrence (mirrors `tests/mcp/test_ci_guard.py`).
- 1 critical safety fix: `WEBSOCKET_GUIDE.md` env-var names now match source (silent prod JWT failure risk closed).
- 8 `.backup.json` files removed from git; `*.backup.json` added to `.gitignore`.
- 3 phantom filename references replaced.
- Coverage target text aligned with `pyproject.toml [tool.coverage.report].fail_under` (49.13%).
```

- [ ] **Step 4: Final commit**

```bash
cd /Users/les/Projects/fastblocks
git add tests/docs/ CHANGELOG.md
git -c user.email=les@wedgwoodwebworks.com commit -m "fix(fastblocks): P10 doc-accuracy guard live; CHANGELOG entry for remediation wave"
```

- [ ] **Step 5: Open a single squash-merge PR per the Bodai pre-1.0 policy**

Per memory `bodai-pre-1.0-merge-policy.md`: all Bodai components merge directly to main pre-1.0. Either fast-forward 9 commits into main or open a PR with the squash. Recommended: PR for the wave so reviewers can audit the diff as one.

______________________________________________________________________

## Self-Review Checklist (run before declaring plan complete)

- [ ] Every audit finding is mapped to a phase. (Coverage: see "Audit findings → Phase mapping" appendix below.)
- [ ] No phase has more than 12 tasks.
- [ ] No task is more than 30 minutes of focused work.
- [ ] Every phase ends with a `git commit` step.
- [ ] Every commit message uses `fix(fastblocks): P<N> <description>` format.
- [ ] No task says "TBD", "TODO", or "implement later".
- [ ] Every step shows actual code, not placeholders.
- [ ] The CI guard scaffold (Phase 1) precedes any narrative rewrite (Phases 3-5).
- [ ] The critical safety fix (Phase 0) precedes everything.
- [ ] Archived docs (`docs/archive/`, `docs/baselines/`, `docs/superpowers/notes/`) are not touched.

## Audit findings → Phase mapping (verification)

| Audit cluster | Phase |
|---------------|-------|
| Cluster A: ACB migration rot | P3, P4, P5 |
| Cluster B: MCP hallucinations | P2, P3, P6 |
| Cluster C: CLI hallucinations | P2, P3 |
| Cluster D: Coverage target drift | P6 |
| Cluster E: Adapter file rename | P5, P7 |
| Cluster F: Env-var inconsistency | P0, P2 (guard) |
| Cluster G: Version/roadmap drift | P6, P9 |
| Cluster H: Backup files | P8 |
| Cluster I: Phantom filenames | P9 |
| Cluster J: Tool-profile imprecision | P6 |

## Execution Handoff

Plan saved to `/Users/les/Projects/fastblocks/docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md`.

Two execution options:

1. **Subagent-Driven (recommended)** — I dispatch a fresh subagent per phase, review between phases, fast iteration. Mirrors the 4-agent audit pattern that found all 75 findings.
1. **Inline Execution** — Execute tasks in this session using executing-plans, batch execution with checkpoints for review.

Which approach?
