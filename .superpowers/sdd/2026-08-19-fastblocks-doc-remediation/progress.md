# SDD ledger — plan: docs/superpowers/plans/2026-08-19-fastblocks-doc-remediation.md

## Branch: docs/audit-remediation-2026-08-19

## Commits

- `6f5e994` P0 critical safety fix (WEBSOCKET_GUIDE env-var)
- `5f12485` P1 CI guard scaffold
- `41ad715` P2 CI guard assertions (xfail baseline)
- `bf989d6` P3 ACB narrative rewrite — README/QWEN/RULES (amended)
- `516fd95` P4 docs/ guide ACB rewrite + WebSocket MCP section deletion
- `0b6dc1b` P5 adapter README ACB rewrite + main.py→default.py + registration

## Task status

- P0: complete (commits 41ad715..6f5e994, review clean)
- P1: complete (commits 6f5e994..5f12485, review clean)
- P2: complete (commits 5f12485..41ad715, review clean)
- P3: complete (commits 41ad715..bf989d6, review approved)
  - Fix round 1/5 (1 addressed, 0 open — resolver API alignment)
  - Concerns 2-6 documented as acceptable observations
- P4: complete (commits bf989d6..516fd95, review approved with findings)
  - Reviewer findings (parked for Phase 10 final review):
    - F1 — `docs/examples/syntax_demo.py:9-10` still imports `from acb.config`, `from acb.depends` (out of P4 scope; pre-existing drift caught by recursive test scan)
    - F3 — `docs/README.md:30,45,73,91` still references phantom filenames (Phase 9 owns this — already in P9 spec)
    - F5 — `broadcast_*` substring match is over-greedy in CI guard; real methods match prohibited patterns. **Phase 10 must tighten with word boundaries before removing the xfail mark**
- P5: complete (commits 516fd95..0b6dc1b, review approved, no findings)
  - `test_no_phantom_adapter_paths` xfail → xpass (main.py removed from app/README.md and routes/README.md)
  - xfail count: 34 → 33
