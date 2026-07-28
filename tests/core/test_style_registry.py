"""Tests for `fastblocks.core.style_registry` (WS-17).

Covers the dynamic `register_<style>_functions` dispatch mechanism itself,
independent of any specific style adapter's own dependencies. Before this
module existed, nothing in `jinja2.py` (or anywhere else in the framework)
ever invoked `register_kelp_functions`/`register_webawesome_functions`
based on `config.app.style` or any other signal -- a direct grep confirmed
zero call sites. This test proves the mechanism that fixes that actually
dispatches correctly, using a fake style module so the test doesn't depend
on any real style adapter's own (potentially heavy/optional) dependencies.
"""

from __future__ import annotations

import sys
import types

import jinja2
import pytest

from fastblocks.core.style_registry import register_style_functions


@pytest.mark.unit
class TestRegisterStyleFunctions:
    def test_noop_when_style_name_is_none(self):
        env = jinja2.Environment()
        baseline = set(env.globals)
        register_style_functions(env, None)
        assert set(env.globals) == baseline

    def test_noop_when_style_name_is_empty(self):
        env = jinja2.Environment()
        baseline = set(env.globals)
        register_style_functions(env, "")
        assert set(env.globals) == baseline

    def test_noop_when_style_module_does_not_exist(self):
        env = jinja2.Environment()
        # Must not raise even though no adapter module exists for this name.
        register_style_functions(env, "nonexistent_style_xyz")

    def test_dispatches_to_a_fake_style_module_by_naming_convention(
        self, monkeypatch
    ):
        """Proves the actual dispatch mechanism -- dynamic import of
        `fastblocks.adapters.style.<name>` + calling
        `register_<name>_functions(env)` -- independent of any real style
        adapter's own dependencies (oneiric, fastblocks_ui, etc.)."""
        calls: list[jinja2.Environment] = []
        fake_module = types.ModuleType("fastblocks.adapters.style.faketeststyle")

        def register_faketeststyle_functions(env: jinja2.Environment) -> None:
            calls.append(env)
            env.globals["fake_test_style_marker"] = True

        fake_module.register_faketeststyle_functions = (  # type: ignore[attr-defined]
            register_faketeststyle_functions
        )
        monkeypatch.setitem(
            sys.modules, "fastblocks.adapters.style.faketeststyle", fake_module
        )

        env = jinja2.Environment()
        register_style_functions(env, "faketeststyle")

        assert calls == [env]
        assert env.globals["fake_test_style_marker"] is True

    def test_errors_inside_register_function_are_swallowed(self, monkeypatch):
        """A style adapter's own bug must not break template rendering for
        everyone else -- matches the defensive `suppress(Exception)`
        convention already used throughout `fastblocks/adapters/style/*.py`."""
        fake_module = types.ModuleType("fastblocks.adapters.style.brokenstyle")

        def register_brokenstyle_functions(env: jinja2.Environment) -> None:
            raise RuntimeError("boom")

        fake_module.register_brokenstyle_functions = (  # type: ignore[attr-defined]
            register_brokenstyle_functions
        )
        monkeypatch.setitem(
            sys.modules, "fastblocks.adapters.style.brokenstyle", fake_module
        )

        env = jinja2.Environment()
        register_style_functions(env, "brokenstyle")  # must not raise

    def test_errors_inside_register_function_are_logged(self, monkeypatch):
        """WS-18 review finding: silently swallowing a broken
        `register_<name>_functions` (as opposed to a simply-missing one)
        reproduces the exact undiscoverable-failure mode this module's
        docstring says kelp.py/webawesome.py suffer from. The exception must
        still not propagate, but it must be logged."""
        fake_module = types.ModuleType("fastblocks.adapters.style.loggedbreak")

        def register_loggedbreak_functions(env: jinja2.Environment) -> None:
            raise AttributeError("boom")

        fake_module.register_loggedbreak_functions = (  # type: ignore[attr-defined]
            register_loggedbreak_functions
        )
        monkeypatch.setitem(
            sys.modules, "fastblocks.adapters.style.loggedbreak", fake_module
        )

        logged: list[tuple[str, tuple[object, ...]]] = []

        class FakeLogger:
            def exception(self, msg, *args):
                logged.append((msg, args))

        import oneiric.core.logging as oneiric_logging

        monkeypatch.setattr(
            oneiric_logging, "get_logger", lambda name: FakeLogger()
        )

        env = jinja2.Environment()
        register_style_functions(env, "loggedbreak")  # must not raise

        assert len(logged) == 1
        assert "loggedbreak" in logged[0][0]

    def test_noop_when_style_module_has_non_callable_register_attr(
        self, monkeypatch
    ):
        fake_module = types.ModuleType("fastblocks.adapters.style.oddstyle")
        fake_module.register_oddstyle_functions = "not a function"  # type: ignore[attr-defined]
        monkeypatch.setitem(
            sys.modules, "fastblocks.adapters.style.oddstyle", fake_module
        )

        env = jinja2.Environment()
        register_style_functions(env, "oddstyle")  # must not raise

    def test_vanilla_style_is_a_noop_today(self):
        """`vanilla` is a real, always-available adapter that ships no Jinja
        globals -- must be silently skipped, not an error, and must not add
        any wa_*/kelp_*-style globals."""
        env = jinja2.Environment()
        baseline = set(env.globals)
        register_style_functions(env, "vanilla")
        assert set(env.globals) == baseline
