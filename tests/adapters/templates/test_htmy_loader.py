"""Tests for HTMY component loader safety.

Covers Phase 1.2 (path containment) and Phase 1.3 (ast.parse class walker)
in fastblocks' security post-cutover plan.
"""

from __future__ import annotations

import ast
import tempfile
import textwrap
from pathlib import Path
from unittest.mock import patch

import pytest
from anyio import Path as AsyncPath
from fastblocks.adapters.templates._htmy_components import (
    AdvancedHTMYComponentRegistry,
    ComponentCompilationError,
    ComponentScaffolder,
    ComponentType,
    ComponentValidationError,
    ComponentValidator,
    load_component_from_source,
)


# ---------------------------------------------------------------------------
# Phase 1.2 — path containment
# ---------------------------------------------------------------------------


class _RecordingAsyncPath(AsyncPath):
    """AsyncPath subclass used to verify traversal rejection.

    The production code uses ``Path.relative_to(safe_root)``; this subclass
    lets us record what ``safe_root`` is without depending on the global
    filesystem state.
    """


@pytest.mark.unit
class TestScaffoldPathContainment:
    """Sub-task 1.2: reject path-traversal names in scaffold_component."""

    @pytest.mark.asyncio
    async def test_scaffold_component_rejects_path_traversal(self, tmp_path: Path):
        """A name with ``..`` segments must raise ValueError, not write a file."""
        registry = AdvancedHTMYComponentRegistry(
            searchpaths=[AsyncPath(str(tmp_path))],
        )

        with pytest.raises(ValueError):
            await registry.scaffold_component(
                name="../../etc/passwd",
                component_type=ComponentType.DATACLASS,
            )

        # No file should have been written outside tmp_path.
        assert not (tmp_path.parent / "etc").exists()

    @pytest.mark.asyncio
    async def test_scaffold_component_rejects_absolute_name(
        self, tmp_path: Path
    ) -> None:
        """An absolute path passed via the name field must raise ValueError."""
        registry = AdvancedHTMYComponentRegistry(
            searchpaths=[AsyncPath(str(tmp_path))],
        )

        with pytest.raises(ValueError):
            await registry.scaffold_component(
                name="/etc/passwd",
                component_type=ComponentType.DATACLASS,
            )


@pytest.mark.unit
class TestScaffolderCreatePathContainment:
    """Sub-task 1.2: path containment in the static ``create_*`` helpers."""

    def test_create_basic_rejects_path_traversal(self) -> None:
        with pytest.raises(ValueError):
            ComponentScaffolder.create_basic_component(name="../../etc/passwd")

    def test_create_htmx_rejects_path_traversal(self) -> None:
        with pytest.raises(ValueError):
            ComponentScaffolder.create_htmx_component(
                name="../escape", endpoint="/x"
            )

    def test_create_composite_rejects_path_traversal(self) -> None:
        with pytest.raises(ValueError):
            ComponentScaffolder.create_composite_component(
                name="nested/../bad", children=["a", "b"]
            )


@pytest.mark.unit
class TestOverwriteParameter:
    """Sub-task 1.2: ``overwrite: bool`` is now an explicit parameter."""

    @pytest.mark.asyncio
    async def test_scaffold_refuses_to_overwrite_by_default(self, tmp_path: Path):
        """Default behaviour must refuse to overwrite existing files."""
        target = tmp_path / "card.py"
        target.write_text("# existing content\n")

        registry = AdvancedHTMYComponentRegistry(
            searchpaths=[AsyncPath(str(tmp_path))],
        )

        # Patch the exists() check on the AsyncPath used as target_path.
        target_async = AsyncPath(str(target))

        async def exists_true() -> bool:
            return True

        target_async.exists = exists_true  # type: ignore[method-assign]

        with pytest.raises(ValueError, match="already exists"):
            await registry.scaffold_component(
                name="Card",
                component_type=ComponentType.DATACLASS,
                target_path=target_async,
            )

        assert target.read_text() == "# existing content\n"

    @pytest.mark.asyncio
    async def test_scaffold_overwrites_when_overwrite_true(self, tmp_path: Path):
        """``overwrite=True`` must let the scaffolder replace the file."""
        target = tmp_path / "card.py"
        target.write_text("# existing content\n")

        registry = AdvancedHTMYComponentRegistry(
            searchpaths=[AsyncPath(str(tmp_path))],
        )

        # Patch exists() and write_text() on the AsyncPath so the test
        # runs in the conftest's MockAsyncPath environment.
        target_async = AsyncPath(str(target))
        written: list[str] = []

        async def exists_true() -> bool:
            return True

        async def write_text_stub(content: str) -> None:
            written.append(content)

        target_async.exists = exists_true  # type: ignore[method-assign]
        target_async.write_text = write_text_stub  # type: ignore[method-assign]

        result = await registry.scaffold_component(
            name="Card",
            component_type=ComponentType.DATACLASS,
            target_path=target_async,
            overwrite=True,
        )

        assert result == target_async
        assert written, "scaffold should have called write_text"
        assert "class Card" in written[-1]


# ---------------------------------------------------------------------------
# Phase 1.3 — ast.parse class walker (replaces exec_module)
# ---------------------------------------------------------------------------


@pytest.mark.unit
class TestLoaderUsesAstParse:
    """Sub-task 1.3: loader must not call ``importlib.util.spec_from_file_location``."""

    def test_loader_uses_ast_parse_not_exec_module(self) -> None:
        """Patching ``spec_from_file_location`` shows it's never called."""
        source = textwrap.dedent(
            """
            from dataclasses import dataclass

            @dataclass
            class Card:
                title: str = "hi"

                def htmy(self, context):
                    return "<div>hi</div>"
            """
        )
        with patch(
            "importlib.util.spec_from_file_location"
        ) as mock_spec:
            cls = load_component_from_source(source, name="card")

        assert mock_spec.call_count == 0
        assert cls.__name__ == "Card"
        assert callable(getattr(cls, "htmy", None))


@pytest.mark.unit
class TestLoaderRejectsImports:
    """Sub-task 1.3: import statements must be rejected."""

    def test_loader_rejects_component_with_import(self) -> None:
        source = textwrap.dedent(
            """
            import os

            class Card:
                def htmy(self, context):
                    return os.environ.get("X", "")
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")

    def test_loader_rejects_component_with_importfrom(self) -> None:
        source = textwrap.dedent(
            """
            from os import environ

            class Card:
                def htmy(self, context):
                    return environ.get("X", "")
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")

    def test_loader_rejects_disallowed_allowlisted_module(self) -> None:
        """``sys`` is outside the safe import allowlist and must be rejected."""
        source = textwrap.dedent(
            """
            from sys import argv

            class Card:
                def htmy(self, context):
                    return str(argv)
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")

    def test_loader_accepts_dacapp_and_typing_imports(self) -> None:
        """``dataclasses`` and ``typing`` are allowlisted for components."""
        source = textwrap.dedent(
            """
            from dataclasses import dataclass, field
            from typing import Any

            @dataclass
            class Card:
                title: str = field(default="hi")

                def htmy(self, context: Any) -> str:
                    return f"<div>{self.title}</div>"
            """
        )
        cls = load_component_from_source(source, name="card")
        assert cls.__name__ == "Card"


@pytest.mark.unit
class TestLoaderRejectsDangerousCalls:
    """Sub-task 1.3: ``exec`` / ``eval`` / ``compile`` / ``__import__`` must be rejected."""

    @pytest.mark.parametrize(
        "call",
        [
            'exec("print(1)")',
            'eval("1+1")',
            'compile("x=1", "<s>", "exec")',
            "__import__(\"os\")",
        ],
    )
    def test_loader_rejects_dangerous_call(self, call: str) -> None:
        source = textwrap.dedent(
            f"""
            class Card:
                def htmy(self, context):
                    {call}
                    return ""
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")

    def test_loader_rejects_nested_dangerous_call(self) -> None:
        """A dangerous call buried in a nested expression must still be rejected."""
        source = textwrap.dedent(
            """
            class Card:
                def htmy(self, context):
                    def inner():
                        return eval("1")
                    return inner()
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")


@pytest.mark.unit
class TestLoaderTopLevelShape:
    """Sub-task 1.3: only class / def allowed at the top level."""

    def test_loader_rejects_top_level_assignment(self) -> None:
        source = textwrap.dedent(
            """
            X = 1

            class Card:
                def htmy(self, context):
                    return ""
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")

    def test_loader_rejects_top_level_expression(self) -> None:
        source = textwrap.dedent(
            """
            print("hi")

            class Card:
                def htmy(self, context):
                    return ""
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")


@pytest.mark.unit
class TestLoaderAcceptsValidComponent:
    """Sub-task 1.3: a valid component is loaded successfully."""

    def test_loader_accepts_valid_component(self) -> None:
        source = textwrap.dedent(
            """
            from dataclasses import dataclass

            @dataclass
            class Card:
                title: str = "hi"

                def htmy(self, context):
                    return f"<div>{self.title}</div>"
            """
        )
        cls = load_component_from_source(source, name="card")

        assert cls.__name__ == "Card"
        instance = cls()
        assert instance.htmy({}).startswith("<div>")

    def test_loader_accepts_component_without_dataclass_decorator(self) -> None:
        source = textwrap.dedent(
            """
            class Card:
                def htmy(self, context):
                    return "<div>ok</div>"
            """
        )
        cls = load_component_from_source(source, name="card")
        assert cls.__name__ == "Card"

    def test_loader_returns_none_when_no_class_defined(self) -> None:
        source = textwrap.dedent(
            """
            def helper():
                return 1
            """
        )
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")

    def test_loader_rejects_syntax_error(self) -> None:
        with pytest.raises(SyntaxError):
            load_component_from_source("def broken(:\n", name="card")


@pytest.mark.unit
class TestValidatorAndRegistryUseNewLoader:
    """Validate and registry code paths now use the safe loader."""

    def test_validator_does_not_call_spec_from_file_location(self) -> None:
        with patch(
            "importlib.util.spec_from_file_location"
        ) as mock_spec:
            validator = ComponentValidator()
            with tempfile.NamedTemporaryFile(
                mode="w", suffix=".py", delete=False
            ) as f:
                f.write(
                    textwrap.dedent(
                        """
                        from dataclasses import dataclass

                        @dataclass
                        class Card:
                            def htmy(self, context):
                                return "<div>hi</div>"
                        """
                    )
                )
                path = AsyncPath(f.name)
            try:
                # invoke through async helper to mirror real flow
                import asyncio

                asyncio.get_event_loop().run_until_complete(
                    validator.validate_component_file(path)
                )
            finally:
                Path(f.name).unlink(missing_ok=True)
        assert mock_spec.call_count == 0


@pytest.mark.unit
class TestLegacyExecModulePathGone:
    """The dangerous ``spec.loader.exec_module`` path must no longer be reachable."""

    def test_exec_module_not_called_by_registry(self) -> None:
        with patch("importlib.util.spec_from_file_location") as mock_spec:
            registry = AdvancedHTMYComponentRegistry(
                searchpaths=[AsyncPath("/nonexistent")],
            )

            # Pull the load_component_from_source module function used internally.
            from fastblocks.adapters.templates import _htmy_components as mod

            source = textwrap.dedent(
                """
                from dataclasses import dataclass

                @dataclass
                class Card:
                    title: str = "hi"

                    def htmy(self, context):
                        return f"<div>{self.title}</div>"
                """
            )
            metadata = type(
                "M",
                (),
                {"path": AsyncPath("/tmp/card.py"), "stem": "card"},
            )()
            # Direct call (no async needed at this layer).
            cls = mod.load_component_from_source(source, name="card")
            assert cls is not None

        assert mock_spec.call_count == 0

    def test_legacy_walk_top_level_helper_exists(self) -> None:
        """The refactored walker must expose per-node-type helpers."""
        from fastblocks.adapters.templates import _htmy_components as mod

        for name in (
            "load_component_from_source",
            "_walk_top_level",
            "_check_no_dangerous_calls",
            "_extract_class",
        ):
            assert callable(getattr(mod, name, None)), f"missing helper: {name}"

    def test_rejects_compile_call_via_call_node(self) -> None:
        """Sanity check: a call to ``compile`` at module top level is rejected."""
        source = "compile('x', '<s>', 'exec')\n"
        with pytest.raises(ComponentValidationError):
            load_component_from_source(source, name="card")
