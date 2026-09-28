"""D9 no-claim-without-evidence lint.

Greps landing templates + README for marketing superlatives. If any are
found without a backing CI artifact (perf benchmark, audit dimension,
test name), the test fails. Per spec section B2 "Three content rules"
rule 1.

# req: REQ-P2-B2-001, REQ-P2-B2-002
"""
from __future__ import annotations

from pathlib import Path

BACKED_CLAIMS: dict[str, list[str]] = {
    "fast": ["test_performance_freshness", ".benchmarks/"],
    "secure": ["test_routes_returns_200", "middleware"],
    # kelp/webawesome removed (per Phase 1A); never appear here.
}

FORBIDDEN_PHRASES: tuple[str, ...] = (
    "lightning-fast",
    "blazing",
    "world-class",
    "blazingly fast",
)


def test_no_unbacked_marketing_claims() -> None:
    """Landing templates + landing README must not contain forbidden marketing phrases.

    Scoped to ``examples/landing/`` per spec B2 — the landing is the
    dogfood surface, not the canonical docs. The main ``README.md`` at
    the repo root is a separate surface with its own review cadence.
    """
    landing_root = Path("/Users/les/Projects/fastblocks/examples/landing")
    files: list[Path] = list(landing_root.rglob("*.html"))
    files.append(landing_root / "README.md")
    files = [p for p in files if p.exists()]

    violations: list[str] = []
    for path in files:
        try:
            text = path.read_text().lower()
        except (OSError, UnicodeDecodeError):
            continue
        for phrase in FORBIDDEN_PHRASES:
            if phrase in text:
                root_key = phrase.split("-")[0].split(" ")[0]
                backing = BACKED_CLAIMS.get(root_key, [])
                backed = any(
                    art in str(landing_root) or art in text for art in backing
                )
                if not backed:
                    violations.append(f"{path}: '{phrase}' has no backing CI artifact")

    assert not violations, "Marketing claims without backing:\n  " + "\n  ".join(violations)
