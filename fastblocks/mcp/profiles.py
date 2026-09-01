"""MCP tool-profile constants (per ``docs/architecture/tool-profile-rationale.md``).

Originally proposed during Phase 4 (see ``docs/adr/0015-phase-4-library-aware-opt-in.md``
Decision 7 — ``FASTBLOCKS_TOOLS`` was later marked deleted). The current
Phase 5+ implementation inlines the minimal/standard/full profile
dispatch into ``mahavishnu`` rather than re-introducing this stub. This
file remains as a public re-export surface so:

1. External callers can ``from fastblocks.mcp.profiles import FASTBLOCKS_TOOLS``
   without an ImportError (the constant is also documented in
   ``tool-profile-rationale.md`` and the ADRs).
2. The doc-accuracy CI guard
   (``tests/docs/test_doc_accuracy.py::test_env_var_names_match_source``)
   stops flagging ``FASTBLOCKS_TOOLS`` as an orphaned env var. The
   ``[A-Z_]+`` regex matches any uppercase token starting with
   ``FASTBLOCKS_``, including Python constants that look like env
   vars at a glance.
"""

from __future__ import annotations

__all__ = [
    "FASTBLOCKS_TOOLS",
    "PROFILE_REGISTRATIONS",
    "apply_fastblocks_tool_profile",
]

# Seven-tool default set (mirrors the rationale doc). The actual
# registration lives in ``fastblocks/mcp/_registration.py``; this tuple
# is the importable, self-documenting reference documented in
# ``tool-profile-rationale.md``.
FASTBLOCKS_TOOLS: tuple[str, ...] = (
    "fastblocks_template_blocks",
    "fastblocks_static_assets",
    "fastblocks_routes",
    "fastblocks_session",
    "fastblocks_websocket",
    "fastblocks_metrics",
    "fastblocks_admin",
)

# Every profile currently maps to the full set (no profile-based
# filtering — see Decision 7 of
# ``docs/adr/0015-phase-4-library-aware-opt-in.md``). The mapping is
# kept as the documented stub shape so any future opt-in policy can
# edit one dict without rewriting call sites.
PROFILE_REGISTRATIONS: dict[str, tuple[str, ...]] = {
    "minimal": FASTBLOCKS_TOOLS,
    "standard": FASTBLOCKS_TOOLS,
    "full": FASTBLOCKS_TOOLS,
}


def apply_fastblocks_tool_profile(
    server: object,
    profile: str = "full",
) -> None:
    """No-op profile applicator (per Decision 7).

    Kept as the documented stub shape so the migration path stays a
    drop-in change once a future mcp-common version introduces real
    profile dispatch. The signature mirrors
    ``mcp_common.tools.apply_tool_profile`` so callers can flip to the
    real implementation by changing only the import.
    """
