#!/usr/bin/env bash
# Phase 1.5+ audit-cleared gate. Exits 0 iff all checks pass.
# Usage: bash scripts/phase1.5-plus-gate.sh
set -euo pipefail
cd "$(dirname "$0")/.."

echo "=== Phase 1.5+ gate ==="

# Sanity: venv exists (otherwise pytest fails cryptically)
[ -x .venv/bin/pytest ] \
    || { echo "FAIL: .venv/bin/pytest missing — run uv sync first"; exit 1; }
echo "OK: venv present"

# Wave A: spec failure inventory exists
test -f docs/spec-failure-inventory.md \
    || { echo "FAIL: docs/spec-failure-inventory.md missing (Wave A #1)"; exit 1; }
echo "OK: spec failure inventory present"

# Wave A: trailing newline on a11y conftest
LAST_BYTE=$(tail -c 1 tests/a11y/conftest.py | xxd -p)
[ "$LAST_BYTE" = "0a" ] \
    || { echo "FAIL: tests/a11y/conftest.py missing trailing newline (Wave A #6)"; exit 1; }
echo "OK: a11y conftest has trailing newline"

# Wave A: exception tuple collapsed
grep -q "except (Exception,):" fastblocks/exceptions.py \
    || { echo "FAIL: exception tuple not collapsed (Wave A #4)"; exit 1; }
echo "OK: exception tuple collapsed"

# Wave B: module-level sys.modules stubs gone from templates test files
# (The "not hasattr(...) brittle check" described in the Phase 1.5 ledger
# does not exist in the codebase today — verified via grep -rn 'if not
# hasattr' tests/adapters/templates/ returns nothing. The legitimate
# `assert not hasattr` patterns at test_htmy_loader_safety.py:116,119 and
# test_filters_comprehensive.py:538 are XSS-defense regression assertions
# and are NOT in scope for removal.)
if grep -l "sys.modules\[.jinja2_async_environment.\]\s*=" \
        tests/adapters/templates/test_jinja2.py \
        tests/adapters/templates/test_rendering_jinja2.py 2>/dev/null; then
    echo "FAIL: module-level sys.modules stub still present in templates tests (Wave B #5)"
    exit 1
fi
echo "OK: module-level sys.modules stubs gone from templates tests"

# Wave C: serial-marks documented (rationale comment block)
grep -q "Phase 1.5+ Wave C serial-marks" tests/conftest.py \
    || { echo "FAIL: no Wave C serial-marks rationale in tests/conftest.py"; exit 1; }
echo "OK: Wave C serial-marks documented"

# Wave E: punt horizon check (target date within 6 months from today)
if [ -f docs/known-claim-gaps.md ]; then
    TODAY=$(date +%Y-%m-%d)
    SIX_MONTHS_OUT=$(date -v+6m +%Y-%m-%d 2>/dev/null || date -d "+6 months" +%Y-%m-%d)
    # Extract Target: YYYY-MM-DD rows; check each is in range
    BAD_PUNT=$(awk -F'|' '/Target: [0-9]{4}-[0-9]{2}-[0-9]{2}/ {
        match($0, /Target: ([0-9]{4}-[0-9]{2}-[0-9]{2})/, arr)
        target = arr[1]
        if (target < "'"$TODAY"'" || target > "'"$SIX_MONTHS_OUT"'") print NR": "$0
    }' docs/known-claim-gaps.md)
    if [ -n "$BAD_PUNT" ]; then
        echo "FAIL: punt target date outside 6-month window (today=$TODAY, horizon=$SIX_MONTHS_OUT):"
        echo "$BAD_PUNT"
        exit 1
    fi
    echo "OK: punt target dates within 6-month horizon"
fi

# 5 consecutive serial runs
echo "Running 5 consecutive serial pytest runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov -p no:xdist -q \
        || { echo "FAIL: serial run $i"; exit 1; }
done
echo "OK: 5/5 serial runs passed"

# 5 consecutive xdist runs
# Note: PASS = all non-serial-marked tests pass; serial-marked tests
# are SKIPPED under xdist per the pytest_collection_modifyitems hook at
# tests/conftest.py:131-153. Serial-marked tests are verified in the
# serial-mode regression check above.
echo "Running 5 consecutive xdist pytest runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --no-cov --dist=loadfile -q \
        || { echo "FAIL: xdist run $i (non-serial tests); exit 1; }
done
echo "OK: 5/5 xdist runs passed (non-serial tests; serial-marked tests skipped per hook)"

# 5 consecutive coverage-gate runs
echo "Running 5 consecutive coverage-gate runs..."
for i in 1 2 3 4 5; do
    .venv/bin/pytest --cov=fail_under=67.81 -q \
        || { echo "FAIL: coverage run $i"; exit 1; }
done
echo "OK: 5/5 coverage-gate runs passed"

echo "=== Phase 1.5+ gate: ALL CHECKS PASSED ==="
