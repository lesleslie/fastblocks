# FastBlocks ty Cleanup Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Reduce ty diagnostics in `/Users/les/Projects/fastblocks/` from 374 to 0, surfacing real bugs inline rather than silently rewiring them.

**Architecture:** Phased by cascade leverage. Phase 1 fixes the 5 root-cause patterns that explain ~244 diagnostics (Resolver API, suppression syntax, invalid-await, Self@init, call-top-callable). Phase 2 addresses residual typing/API issues. Phase 3 removes redundant casts. Phase 4 is the gate. Each phase is verified with `uv run ty check fastblocks/` and `uv run pytest -m "not slow"` before the next phase begins.

**Tech Stack:** ty (Astral type checker), Python 3.13, Oneiric resolver, Mahavishnu-style CLI tests.

## Global Constraints

- Spec at `docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md` is the source of truth for scope.
- Production code only (`fastblocks/`); test changes allowed only when a test verifies genuinely broken behavior.
- `uv run ty check fastblocks/` must drop strictly between phases.
- `uv run pytest -q -m "not slow" --no-header` must remain ≥ 1714 passing throughout.
- Real bugs must be surfaced inline (see spec's "Real-bug policy") — not silently fixed.
- ty ignore syntax: `# ty: ignore[rule-code]` (not bare `# type: ignore`).
- Don't commit the working tree's pre-existing dirty state (those modifications belong to earlier work).
- Commit per logical boundary (single file or single phase). Use `git commit -- <pathspec>` after the spec's permission gotcha is mitigated (use plain `git commit` for cleanup commits, per project memory).

______________________________________________________________________

## Task 1: Phase 1a — Resolver API mapping

**Files:**

- Modify: many files across `fastblocks/` that reference `Resolver.set`, `Resolver.get_sync`, or `Resolver.config`
- Likely hot spots: `fastblocks/__init__.py`, `fastblocks/adapters/oneiric_helper.py`, `fastblocks/mcp/registry.py`, `fastblocks/**/*.py` (broad grep)
- Reference: `oneiric.core.resolution.Resolver` in `.venv/lib/python3.13/site-packages/oneiric/core/resolution.py`

**Interfaces:**

- The `Resolver` API actually exposes: `explain`, `list_active`, `list_shadowed`, `register`, `register_from_pkg`, `resolve`, `register_pkg` (factory function — call with `registry`, `package_name`, `path`, `candidates`)

- Mapping the wrong-API calls to the right API is the deliverable.

- [ ] **Step 1: Read the actual Resolver source to confirm the API**

```bash
cd /Users/les/Projects/fastblocks
sed -n '1,200p' .venv/lib/python3.13/site-packages/oneiric/core/resolution.py
```

Note every public method and its signature.

- [ ] **Step 2: Inventory all wrong-API call sites**

```bash
cd /Users/les/Projects/fastblocks
grep -rn "depends.get_sync\|depends\.set\b\|depends\.config\|resolver\.get_sync\|resolver\.set\b\|resolver\.config" fastblocks/ \
  | tee /tmp/ty-phase1a-sites.txt
wc -l /tmp/ty-phase1a-sites.txt
```

Expected: ~145 lines.

- [ ] **Step 3: Categorize each site into one of three buckets**

For each line in `/tmp/ty-phase1a-sites.txt`, note:

- **Bucket A** — clear mapping to existing API (e.g., `get_sync(name)` → `resolve(domain, name)`). Apply mechanically.
- **Bucket B** — code calls a method that has no equivalent (truly dead code path). Surface as a real bug per the spec's "Real-bug policy". Do NOT silently rewire.
- **Bucket C** — code accesses `depends.config.X` where `config` is a public attribute on the underlying Config object but not on Resolver. May need to import the config object directly.

Output one summary per bucket to a comment block in the first file you edit, then proceed.

- [ ] **Step 4: Apply Bucket A fixes**

For each clear-mapping site, edit the file and replace the wrong API call with the correct one. Each replacement is a single edit. Run ty between every 5-10 edits to catch cascading effects.

- [ ] **Step 5: For each Bucket B site, document the bug and stop**

Per the spec's real-bug policy: surface the file, line, wrong API call, and corrected API. Ask the user before fixing. Add a one-line entry to the spec's "Real bugs found" section.

- [ ] **Step 6: For each Bucket C site, verify the type of `depends.config` or equivalent**

Read the calling code; if `depends.config.X` is reaching for a config object that exists, locate the canonical import and rewire. If not, surface as a real bug.

- [ ] **Step 7: Verify Phase 1a**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"
```

Expected: significantly lower than 374 (target: drop ≥ 100 from the 145 wrong-API count).

```bash
cd /Users/les/Projects/fastblocks
uv run pytest -q -m "not slow" --no-header
```

Expected: ≥ 1714 pass, 0 fail.

- [ ] **Step 8: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/  # Only the files you edited
git commit -m "fix(fastblocks): map wrong Resolver API calls to correct surface

get_sync → resolve, set → register, config → <canonical> per Bucket
mapping in docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

______________________________________________________________________

## Task 2: Phase 1b — Suppression syntax cleanup

**Files:**

- Modify: any file with a bare `# type: ignore` (no `[rule]` suffix)

**Interfaces:**

- ty syntax: `# ty: ignore[rule-code]` — discover the rule code by running ty on the line without the comment first.

- [ ] **Step 1: Inventory all bare `# type: ignore` comments**

```bash
cd /Users/les/Projects/fastblocks
grep -rn "# type: ignore$" fastblocks/ | tee /tmp/ty-phase1b-sites.txt
wc -l /tmp/ty-phase1b-sites.txt
```

Expected: ~33 lines.

- [ ] **Step 2: For each site, run ty without the comment to discover the actual rule**

For each file:line in the inventory, read the file around the line, identify the offending line, and run ty on the file with the `# type: ignore` comment temporarily deleted from a copy:

```bash
cd /Users/les/Projects/fastblocks
mkdir -p /tmp/ty-phase1b
cp fastblocks/path/to/offending.py /tmp/ty-phase1b/
# Edit the copy with the Edit tool to remove the # type: ignore line
uv run ty check /tmp/ty-phase1b/offending.py | head -20
```

The error message includes `[rule-code]` in the form `error[rule-code]:`. Capture it. Never modify the original file with sed in this step.

- [ ] **Step 3: Categorize each site into one of two buckets**

- **Bucket A** — bare comment was masking a real error. Replace `# type: ignore` with `# ty: ignore[rule-code]`.

- **Bucket B** — the underlying code was already fixed; the comment is now stale. Just remove the comment.

- [ ] **Step 4: Apply Bucket A fixes**

For each real-error site, replace the bare comment with the typed ty syntax. Verify with ty that the rule-code is exact.

- [ ] **Step 5: Apply Bucket B fixes**

For each stale comment, remove the comment line.

- [ ] **Step 6: Verify Phase 1b**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "unused-type-ignore-comment"
```

Expected: 0.

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"
```

Expected: lower than end of Phase 1a (note: may briefly rise as newly-visible errors emerge; that's expected).

```bash
cd /Users/les/Projects/fastblocks
uv run pytest -q -m "not slow" --no-header
```

Expected: ≥ 1714 pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/
git commit -m "fix(fastblocks): convert bare # type: ignore to ty syntax or remove

ty uses # ty: ignore[rule-code], not the blanket mypy syntax. Removed
33 stale suppressions; corrected the rest with explicit rule codes.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

______________________________________________________________________

## Task 3: Phase 1c — invalid-await cleanup

**Files:**

- Modify: any file with `await depends.` or `await resolver.` where the resolver returns a sync `Candidate`

**Interfaces:**

- `Candidate | None` is sync. Drop `await` at call sites.

- [ ] **Step 1: Inventory all `await depends.` / `await resolver.` patterns**

```bash
cd /Users/les/Projects/fastblocks
grep -rn "await depends\.\|await resolver\." fastblocks/ | tee /tmp/ty-phase1c-sites.txt
wc -l /tmp/ty-phase1c-sites.txt
```

Expected: ~28 lines.

- [ ] **Step 2: For each site, verify the inner call returns a sync value**

Read the resolver return type (or simply test without `await`):

```bash
# Temporarily remove the await keyword and re-run ty
sed -i 's/await depends\./depends./' /tmp/test-file.py
uv run ty check /tmp/test-file.py
```

If the error is gone, the fix is correct. If a different error appears, the code path is more complex and needs investigation.

- [ ] **Step 3: Categorize each site**

- **Bucket A** — straightforward `await depends.get(...)`/`set(...)` etc. where dropping `await` resolves the error. Apply the fix.

- **Bucket B** — code clearly expects an async path (e.g., uses `await` for side effects in a coroutine). Surface as a real bug per the spec's "Real-bug policy" — the resolver may have been async in an older version, or the code is shaped for a different API.

- [ ] **Step 4: Apply Bucket A fixes**

For each clean drop-the-await site, edit the file. Use `Edit` not `sed` for traceability.

- [ ] **Step 5: For each Bucket B site, document and stop**

Surface the bug. Note: many of these are likely the same pattern as the earlier `discovery.py:249` fix (code calling a method that never existed, masked by `await`).

- [ ] **Step 6: Verify Phase 1c**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "invalid-await"
```

Expected: 0.

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"
```

Expected: lower than end of Phase 1b.

```bash
cd /Users/les/Projects/fastblocks
uv run pytest -q -m "not slow" --no-header
```

Expected: ≥ 1714 pass.

- [ ] **Step 7: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/
git commit -m "fix(fastblocks): drop await on sync Resolver returns

Candidate | None is sync; the awaited form was wrong-shaped code per
Resolver's actual API.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

______________________________________________________________________

## Task 4: Phase 1d — Self@init / `_sanitizer` / `_publisher`

**Files:**

- Modify: any class whose methods reference `self._sanitizer`, `self._publisher`, or similar attributes before/aside from initialization

**Interfaces:**

- These are likely real bugs: an attribute is referenced but never set in `__init__` (or set under a different name).

- [ ] **Step 1: Inventory all `Self@...` errors with their referenced attributes**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -B 1 "no attribute \`_sanitizer\`\|no attribute \`_publisher\`\|no attribute \`_something\`" | tee /tmp/ty-phase1d-sites.txt
```

Note that error messages use the form `Object of type Self@<method>` followed by `no attribute '<attr>'`.

- [ ] **Step 2: For each site, locate the class and read its `__init__`**

For each file:line in the inventory, open the file at the class containing the method. Read the `__init__`. Check whether the attribute is set.

- [ ] **Step 3: Categorize each site**

- **Bucket A** — attribute is missing from `__init__`. Fix: add the initialization (likely as `self._sanitizer = None` or similar — match the type the consumer expects).

- **Bucket B** — attribute is set under a different name (typo). Fix: rename one side to match.

- **Bucket C** — code path is conditional and the attribute is set lazily elsewhere. Verify the lazy set exists; if so, fix the type annotation on the attribute to declare `Optional[T]` or similar.

- [ ] **Step 4: Apply Bucket A fixes**

Add the missing `self.<attr> = <init>` to `__init__`. If the attribute type is unclear, use `Any` for now and tighten in Phase 2.

- [ ] **Step 5: Apply Bucket B fixes**

Rename for consistency. Single rename per typo.

- [ ] **Step 6: For each Bucket C site, verify and add the annotation**

If the lazy set is correct, add the type annotation to the class-level declaration (e.g., `self._sanitizer: T | None = None`).

- [ ] **Step 7: Verify Phase 1d**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "Self@\|no attribute \`_sanitizer\`\|no attribute \`_publisher\`"
```

Expected: 0.

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"
```

Expected: lower than end of Phase 1c.

```bash
cd /Users/les/Projects/fastblocks
uv run pytest -q -m "not slow" --no-header
```

Expected: ≥ 1714 pass.

- [ ] **Step 8: Document Bucket B and C findings inline**

For any Bucket B (typo) or Bucket C (lazy init) findings, add a one-line entry to the spec's "Real bugs found" section noting the file and the fix.

- [ ] **Step 9: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/
git commit -m "fix(fastblocks): initialize _sanitizer / _publisher / similar attrs

Several methods referenced self-attribs that weren't set in __init__.
Some were typos; some were lazy-init code paths missing the type
annotation.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

______________________________________________________________________

## Task 5: Phase 1e — call-top-callable + Top[...]

**Files:**

- Modify: any file with `candidate.factory()` or similar untyped callable invocation
- Likely hot spots: `fastblocks/mcp/tools.py`, `fastblocks/middleware.py`

**Interfaces:**

- Fix: either annotate the factory callable's `__call__` return type, or cast at the call site.

- [ ] **Step 1: Inventory all `call-top-callable` errors**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -B 2 "call-top-callable" | tee /tmp/ty-phase1e-sites.txt
```

- [ ] **Step 2: For each site, locate the factory callable's definition**

`candidate.factory` is accessed at the call site, but the type of `factory` is determined by the `Candidate` class in `oneiric.core.resolution`. Read the `Candidate` definition:

```bash
cd /Users/les/Projects/fastblocks
grep -n "factory" .venv/lib/python3.13/site-packages/oneiric/core/resolution.py | head -30
```

- [ ] **Step 3: Categorize each call site**

- **Bucket A** — factory is constructed dynamically and the local code uses untyped input. Fix: cast at the call site: `factory = cast(Callable[..., X], candidate.factory)`.

- **Bucket B** — factory class has a `__call__` that is untyped. Add a return type annotation.

- **Bucket C** — the call-site signature doesn't match `factory()`. Likely the call site is wrong (extra/lacking args). Surface as a real bug.

- [ ] **Step 4: Apply Bucket A fixes**

For each dynamic call site, add the import and `cast().` Note: do not add `# type: ignore` — prefer the cast.

- [ ] **Step 5: Apply Bucket B fixes**

For each factory class with untyped `__call__`, add the return type annotation. If the class is in Oneiric (not fastblocks), the fix is at the call site only (Bucket A).

- [ ] **Step 6: For each Bucket C site, document and stop**

Surface. Likely real bug — wrong call shape.

- [ ] **Step 7: Verify Phase 1e**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "call-top-callable"
```

Expected: 0.

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"
```

Expected: lower than end of Phase 1d.

```bash
cd /Users/les/Projects/fastblocks
uv run pytest -q -m "not slow" --no-header
```

Expected: ≥ 1714 pass.

- [ ] **Step 8: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/
git commit -m "fix(fastblocks): annotate factory callables + cast at dynamic sites

Top[(...) -> object] is not safe to call. Annotate factory __call__
where owned; cast at call sites where factory is dynamically constructed.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

______________________________________________________________________

## Task 6: Phase 2 — Annotation & API-type fixes

**Files:**

- Modify: any file with `unresolved-reference`, `unresolved-import`, `invalid-argument-type`, `missing-argument`, `invalid-method-override`, `invalid-assignment`, `invalid-return-type`, or one-off errors

**Interfaces:**

- This phase is iterative. After Phase 1, re-run ty and work the residual list by category.

- [ ] **Step 1: Re-run ty and bucket the remaining errors**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -E "^(error|warning)\[" | sort | uniq -c | sort -rn
```

Note which categories still have entries. (Expected: ~60 total, dominated by `unresolved-reference`, `invalid-argument-type`, `unresolved-import`, `invalid-method-override`, `invalid-assignment`, `invalid-return-type`, and one-offs.)

- [ ] **Step 2: Phase 2a — Fix `unresolved-reference` (10 expected)**

For each `Name \`<name>\` used when not defined\`:

- `root_path` (7) — likely a missing parameter or import. Find the actual function/method definition and either add the parameter or import the symbol. Surface as a real bug if `root_path` is genuinely undefined.

- `get_adapters`, `get_adapter`, `reload_config` — define or import per the actual API.

- [ ] **Step 3: Phase 2b — Fix `unresolved-import` (6 expected)**

```bash
cd /Users/les/Projects/fastblocks
grep -rn "oneiric.adapters.discovery\|from oneiric.adapters.discovery" fastblocks/
```

Locate the actual module path. Either update the import or remove it if the symbol is no longer used.

- [ ] **Step 4: Phase 2c — Fix `invalid-argument-type` (12 expected)**

The likely pattern is `EventPriority.HIGH` (int) being passed where `EventPriority` is expected. Check the enum definition:

```bash
cd /Users/les/Projects/fastblocks
grep -rn "class EventPriority" fastblocks/
```

If the enum members are typed correctly, this is a stale `# type: ignore[arg-type]` from Phase 1b. If they're not, fix the source.

- [ ] **Step 5: Phase 2d — Fix `missing-argument` (3 expected)**

`register_pkg()` called with no args. Needs `registry`, `package_name`, `path`, `candidates`. Find the call site, read the actual call's intent, and supply the args from the surrounding context. Surface as a real bug if the call site has no clear value to pass.

- [ ] **Step 6: Phase 2e — Fix `invalid-method-override` (7 expected)**

For each override that doesn't match the parent's signature, fix the override. Often these are missing `Optional` annotations or wrong return types.

- [ ] **Step 7: Phase 2f — Fix `invalid-assignment` (6 expected)**

The typical pattern is `Depends.get(...)` returning `object` being assigned to a typed local. The fix is upstream in Phase 1a; this bucket should be empty or near-empty after Phase 1.

- [ ] **Step 8: Phase 2g — Fix `invalid-return-type` (7 expected)**

For each return type mismatch, fix the function's return path or the annotation. Often cascading from upstream fixes.

- [ ] **Step 9: Phase 2h — Fix one-offs (8 expected)**

For each one-off (`not-iterable`, `unsupported-operator`, `too-many-positional-arguments`, `not-subscriptable`, `call-non-callable`), fix in place. Surface as a real bug if the code is genuinely wrong.

- [ ] **Step 10: Verify Phase 2**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"
```

Expected: ≤ 50 (the 5 redundant casts).

```bash
cd /Users/les/Projects/fastblocks
uv run pytest -q -m "not slow" --no-header
```

Expected: ≥ 1714 pass.

- [ ] **Step 11: Commit per sub-phase**

For each 2a–2h, commit the changes with a descriptive message. Don't batch into one giant commit.

______________________________________________________________________

## Task 7: Phase 3 — Remove redundant casts

**Files:**

- Modify: any file with `redundant-cast` warning

- [ ] **Step 1: Inventory all redundant casts**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -B 1 "redundant-cast" | tee /tmp/ty-phase3-sites.txt
```

Expected: 5 lines.

- [ ] **Step 2: For each site, remove the `cast()` call**

The `cast()` is a no-op. Remove the import if it's no longer needed.

- [ ] **Step 3: Verify Phase 3**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "redundant-cast"
```

Expected: 0.

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/ 2>&1 | grep -c "error\|warning"
```

Expected: 0.

- [ ] **Step 4: Commit**

```bash
cd /Users/les/Projects/fastblocks
git add fastblocks/
git commit -m "fix(fastblocks): remove 5 redundant-cast calls

Phase 3 of docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

______________________________________________________________________

## Task 8: Phase 4 — Final verification & gate

**Files:**

- Read-only: `docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md` (the "Real bugs found" section, for the report)

- [ ] **Step 1: ty is clean**

```bash
cd /Users/les/Projects/fastblocks
uv run ty check fastblocks/
```

Expected: "All checks passed!"

- [ ] **Step 2: pytest is still green**

```bash
cd /Users/les/Projects/fastblocks
uv run pytest -q -m "not slow" --no-header
```

Expected: ≥ 1714 pass, 0 fail.

- [ ] **Step 3: crackerjack ty hook passes**

```bash
cd /Users/les/Projects/fastblocks
crackerjack run
```

If the full run exceeds time, scope to the ty hook only:

```bash
cd /Users/les/Projects/fastblocks
uv run python -m crackerjack.tools.ty_ratchet --split
```

Expected: ty hook reports PASS (0/0 or 0/50).

- [ ] **Step 4: Append the final report to the spec**

Open `docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md` and replace the "Real bugs found" running log with the final tally:

- Total diagnostics at start: 374

- Total diagnostics at end: 0

- Real bugs found: [list]

- Phases committed: [list of commit hashes]

- [ ] **Step 5: Commit the spec update**

```bash
cd /Users/les/Projects/fastblocks
git add docs/superpowers/specs/2026-08-20-fastblocks-ty-cleanup-design.md
git commit -m "spec(fastblocks): append ty cleanup final report (374 → 0)

Lists real bugs found, phases committed, and final diagnostic count.

Co-Authored-By: Claude <noreply@anthropic.com>"
```

- [ ] **Step 6: Final report to user**

Send a one-paragraph summary with:

- Total diagnostics reduced (374 → 0)
- Real bugs surfaced (count + list)
- Phase commits (list)
- One next command if needed
