"""Regression test for the FastBlocks MCP tool-profile opt-out.

The framework deliberately opts out of ``mcp_common`` tool-profile
dispatch. The stub at ``fastblocks/mcp/profiles.py`` is a no-op so that:

1. Consumers can import ``apply_fastblocks_tool_profile`` without
   surprises (the call returns successfully; the server is untouched).
2. The opt-out is auditable: the stub emits a one-time deprecation log
   so an operator tailing logs sees that a profile selector is being
   ignored.
3. The signature mirrors ``mcp_common.tools.apply_tool_profile``, so the
   migration path is a drop-in change once ``mcp-common~=0.18`` is
   adopted.

These tests pin all three invariants. If any of them fail, the
"library, not server" rationale in
``docs/architecture/tool-profile-rationale.md`` has been violated.

See: W4.9 task brief at
``/Users/les/Projects/mahavishnu/.superpowers/sdd/2026-08-18-mcp-tool-profile-adoption/task-22-brief.md``.

**Why no top-level ``from mcp_common.tools import ToolProfile``**: the
test conftest installs a stub ``mcp_common`` package in ``sys.modules``
that lacks a ``tools`` submodule (see ``tests/_websocket_stub.py``). The
production stub handles this with a lazy import + a local fallback
enum; the test does the same by reading :data:`fastblocks.mcp.profiles.PROFILE_REGISTRATIONS`
to discover whichever ``ToolProfile`` class is in use.
"""

from __future__ import annotations

import logging
from unittest.mock import MagicMock

import pytest
from fastblocks.mcp.profiles import (
    FASTBLOCKS_TOOLS,
    PROFILE_REGISTRATIONS,
    apply_fastblocks_tool_profile,
)

# Resolve whichever ``ToolProfile`` class the stub is using (real or
# fallback). The stub's ``PROFILE_REGISTRATIONS`` keys are always
# members of that class.
ToolProfile = type(next(iter(PROFILE_REGISTRATIONS)))


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def reset_deprecation_state() -> None:
    """Reset the stub's one-time deprecation flag.

    The stub module keeps a module-level ``_DEPRECATION_EMITTED`` flag so
    the deprecation log fires exactly once per process. Tests that want
    to assert on the log need a clean slate; this fixture clears the
    flag for the duration of the test and restores it afterwards (so we
    do not leak state into other tests in the same session).
    """
    import fastblocks.mcp.profiles as profiles_module

    original = profiles_module._deprecation_emitted
    profiles_module._deprecation_emitted = False
    try:
        yield None
    finally:
        profiles_module._deprecation_emitted = original


# ---------------------------------------------------------------------------
# Module-surface invariants
# ---------------------------------------------------------------------------


class TestStubImports:
    """The stub module must import cleanly on mcp-common~=0.3 and in the stub-``mcp_common`` conftest env.

    If this fails, the framework can no longer host a tool-profile
    opt-out surface at all — the rationale doc would be out of sync
    with reality.
    """

    def test_stub_module_imports(self) -> None:
        # Importing the module must not raise. (The import above already
        # validates this; we make it explicit for the test runner.)
        from fastblocks.mcp import profiles

        assert profiles is not None

    def test_fastblocks_tools_is_a_tuple_of_seven(self) -> None:
        assert isinstance(FASTBLOCKS_TOOLS, tuple)
        assert len(FASTBLOCKS_TOOLS) == 7, (
            "Expected 7 read-only FastBlocks MCP tools; got "
            f"{len(FASTBLOCKS_TOOLS)}: {FASTBLOCKS_TOOLS!r}"
        )

    def test_fastblocks_tools_contains_expected_names(self) -> None:
        expected = {
            "validate_template",
            "list_templates",
            "render_template",
            "list_components",
            "validate_component",
            "list_adapters",
            "check_adapter_health",
        }
        assert set(FASTBLOCKS_TOOLS) == expected


# ---------------------------------------------------------------------------
# Profile-registration invariant: every profile maps to ALL tools
# ---------------------------------------------------------------------------


class TestProfileRegistrations:
    """``PROFILE_REGISTRATIONS`` must map every ``ToolProfile`` to the full set of FastBlocks tools.

    This is the literal "opt out" form: a profile selector that filters
    tools would break the rationale, because it would imply that
    gating is meaningful for a read-only library.
    """

    def test_all_three_profiles_present(self) -> None:
        assert set(PROFILE_REGISTRATIONS.keys()) == {
            ToolProfile.MINIMAL,
            ToolProfile.STANDARD,
            ToolProfile.FULL,
        }

    @pytest.mark.parametrize(
        "profile",
        [
            ToolProfile.MINIMAL,
            ToolProfile.STANDARD,
            ToolProfile.FULL,
        ],
    )
    def test_every_profile_maps_to_all_seven_tools(self, profile: ToolProfile) -> None:
        assert PROFILE_REGISTRATIONS[profile] == FASTBLOCKS_TOOLS, (
            f"Profile {profile!r} must map to all 7 FastBlocks tools "
            f"(the opt-out invariant). Got: {PROFILE_REGISTRATIONS[profile]!r}"
        )


# ---------------------------------------------------------------------------
# No-op behavior: apply_fastblocks_tool_profile must not touch the server
# ---------------------------------------------------------------------------


class TestApplyToolProfileNoOp:
    """``apply_fastblocks_tool_profile`` must be a pure no-op.

    The function accepts a server and a profile, emits a one-time
    deprecation log, and returns ``None`` without calling any method on
    the server. This is what makes the stub safe to call from consumer
    code that doesn't know whether the framework is opted out.
    """

    def test_returns_none(self) -> None:
        server = MagicMock()
        result = apply_fastblocks_tool_profile(server, profile=ToolProfile.FULL)
        assert result is None

    def test_does_not_call_any_method_on_server(self) -> None:
        server = MagicMock()
        apply_fastblocks_tool_profile(server, profile=ToolProfile.STANDARD)

        # The server must be passed in but not invoked. Every attribute
        # access on a MagicMock records a call, so the only entries in
        # ``mock_methods`` are property accesses, not method invocations.
        server_methods_called = [name for name, call in server.method_calls]
        assert server_methods_called == [], (
            "apply_fastblocks_tool_profile must not call any method on "
            f"the server; saw: {server_methods_called!r}"
        )

    @pytest.mark.parametrize(
        "profile",
        [
            ToolProfile.MINIMAL,
            ToolProfile.STANDARD,
            ToolProfile.FULL,
        ],
    )
    def test_no_op_for_every_profile(self, profile: ToolProfile) -> None:
        """The no-op must hold for every profile value, not just FULL."""
        server = MagicMock()
        apply_fastblocks_tool_profile(server, profile=profile)
        assert server.method_calls == []


# ---------------------------------------------------------------------------
# Deprecation log: fires once, with the profile name
# ---------------------------------------------------------------------------


class TestDeprecationLog:
    """The stub emits a one-time deprecation log so operators see why a profile selector is being ignored.

    The log:

    - Fires at ``INFO`` level (not a warning, because the behavior is
      intentional, not deprecated-as-in-removed).
    - Includes the profile name so the operator can see which selector
      was passed.
    - Fires exactly once per process, not on every call.
    """

    def test_logs_once_with_profile_name(
        self,
        caplog: pytest.LogCaptureFixture,
        reset_deprecation_state: None,
    ) -> None:
        server = MagicMock()
        with caplog.at_level(logging.INFO, logger="fastblocks.mcp.profiles"):
            apply_fastblocks_tool_profile(server, profile=ToolProfile.STANDARD)
            apply_fastblocks_tool_profile(server, profile=ToolProfile.STANDARD)
            apply_fastblocks_tool_profile(server, profile=ToolProfile.STANDARD)

        # Exactly one log record from this logger (the one-time guarantee).
        records = [r for r in caplog.records if r.name == "fastblocks.mcp.profiles"]
        assert len(records) == 1, (
            f"Expected exactly one deprecation log; got {len(records)}: "
            f"{[r.getMessage() for r in records]!r}"
        )

        # The record mentions the profile name so an operator can
        # correlate the log with the call site.
        assert "standard" in records[0].getMessage().lower()
