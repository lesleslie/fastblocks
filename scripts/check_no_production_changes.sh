#!/usr/bin/env bash
# Strict-tests-only boundary enforcer (Erratum 10).
# Exits non-zero if any path under fastblocks/ appears in the changeset,
# excluding fastblocks/adapters/templates/htmy_components/** (Phase 1B added
# these and they're outside this canary's scope).

set -e

CHANGESET=$(git diff --name-only main..HEAD)

# Check for production-code paths in fastblocks/ outside the excluded patterns
VIOLATIONS=$(echo "$CHANGESET" | \
    grep -E '^fastblocks/' | \
    grep -vE '^fastblocks/adapters/templates/htmy_components/' || true)

if [ -n "$VIOLATIONS" ]; then
    echo "ERROR: Production code changes detected in changeset:"
    echo "$VIOLATIONS"
    echo ""
    echo "Phase 5 is strictly tests-only. If a production-code change is"
    echo "intentional, amend the strict-tests-only boundary with explicit ADR."
    exit 1
fi

echo "OK: no production code changes"
exit 0
