"""Real CLI invocations via typer.testing.CliRunner for fastblocks/cli.py coverage."""
# pyright: reportAttributeAccessIssue=false

from __future__ import annotations

import sys
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from typer.testing import CliRunner


@pytest.fixture
def runner() -> CliRunner:
    return CliRunner()


@pytest.fixture
def fb_cli():
    from fastblocks.cli import cli

    return cli


def _async_resolver(return_value):
    """Resolver class mock where .resolve() is an AsyncMock."""
    instance = MagicMock()
    instance.resolve = AsyncMock(return_value=return_value)
    return MagicMock(return_value=instance)


def _sync_resolver(return_value):
    """Resolver class mock where .resolve() is a plain MagicMock (components cmd)."""
    instance = MagicMock()
    instance.resolve = MagicMock(return_value=return_value)
    return MagicMock(return_value=instance)


@pytest.mark.unit
class TestVersionCommand:
    def test_version_exits_cleanly(self, runner, fb_cli):
        result = runner.invoke(fb_cli, ["version"])
        assert result.exit_code == 0


@pytest.mark.unit
class TestRunCommand:
    def test_run_default_calls_uvicorn(self, runner, fb_cli):
        with patch("fastblocks.cli.setup_signal_handlers") as mock_signals:
            with patch("fastblocks.cli.uvicorn") as mock_uvicorn:
                result = runner.invoke(fb_cli, ["run"])
        assert result.exit_code == 0
        mock_signals.assert_called_once()
        mock_uvicorn.run.assert_called_once()
        assert mock_uvicorn.run.call_args[1]["lifespan"] == "on"

    def test_run_docker_calls_execute(self, runner, fb_cli):
        with patch("fastblocks.cli.execute") as mock_exec:
            result = runner.invoke(fb_cli, ["run", "--docker"])
        assert result.exit_code == 0
        mock_exec.assert_called_once()

    def test_run_granian_calls_serve(self, runner, fb_cli):
        with patch("fastblocks.cli.setup_signal_handlers"):
            with patch("fastblocks.cli.Granian") as mock_granian:
                with patch.dict(sys.modules, {"granian.constants": MagicMock()}):
                    result = runner.invoke(fb_cli, ["run", "--granian"])
        assert result.exit_code == 0
        mock_granian.return_value.serve.assert_called_once()

    def test_run_custom_host_passed_to_uvicorn(self, runner, fb_cli):
        with patch("fastblocks.cli.setup_signal_handlers"):
            with patch("fastblocks.cli.uvicorn") as mock_uvicorn:
                result = runner.invoke(fb_cli, ["run", "--host", "0.0.0.0"])  # nosec B104
        assert result.exit_code == 0
        assert mock_uvicorn.run.call_args[1]["host"] == "0.0.0.0"  # nosec B104


@pytest.mark.unit
class TestDevCommand:
    def test_dev_default_uses_uvicorn_reload(self, runner, fb_cli):
        with patch("fastblocks.cli.setup_signal_handlers"):
            with patch("fastblocks.cli.uvicorn") as mock_uvicorn:
                result = runner.invoke(fb_cli, ["dev"])
        assert result.exit_code == 0
        kwargs = mock_uvicorn.run.call_args[1]
        assert kwargs["reload"] is True
        assert kwargs["lifespan"] == "on"

    def test_dev_granian_calls_serve_with_reload(self, runner, fb_cli):
        with patch("fastblocks.cli.setup_signal_handlers"):
            with patch("fastblocks.cli.Granian") as mock_granian:
                with patch.dict(sys.modules, {"granian.constants": MagicMock()}):
                    result = runner.invoke(fb_cli, ["dev", "--granian"])
        assert result.exit_code == 0
        mock_granian.return_value.serve.assert_called_once()
        assert mock_granian.call_args[1]["reload"] is True


@pytest.mark.unit
class TestComponentsCommand:
    def test_components_no_registry(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _sync_resolver(None)):
            result = runner.invoke(fb_cli, ["components"])
        assert result.exit_code == 0
        assert "Adapter registry not available" in result.output

    def test_components_with_adapters_listed(self, runner, fb_cli):
        mock_adapter = MagicMock()
        mock_adapter.name = "jinja2"
        mock_adapter.category = "templates"
        mock_adapter.installed = True
        mock_adapter.enabled = True
        mock_adapter.module = "fastblocks.adapters.templates.jinja2"
        mock_registry = MagicMock()
        mock_registry.get_all_adapters.return_value = [mock_adapter]
        with patch("oneiric.core.resolution.Resolver", _sync_resolver(mock_registry)):
            result = runner.invoke(fb_cli, ["components"])
        assert result.exit_code == 0
        assert "jinja2" in result.output

    def test_components_empty_adapter_list(self, runner, fb_cli):
        mock_registry = MagicMock()
        mock_registry.get_all_adapters.return_value = []
        with patch("oneiric.core.resolution.Resolver", _sync_resolver(mock_registry)):
            result = runner.invoke(fb_cli, ["components"])
        assert result.exit_code == 0
        assert "No adapters found" in result.output

    def test_components_resolver_exception(self, runner, fb_cli):
        bad = MagicMock()
        bad.resolve = MagicMock(side_effect=RuntimeError("boom"))
        with patch("oneiric.core.resolution.Resolver", MagicMock(return_value=bad)):
            result = runner.invoke(fb_cli, ["components"])
        assert result.exit_code == 0
        assert "No adapters found" in result.output


@pytest.mark.unit
class TestScaffoldCommand:
    def test_scaffold_no_htmy_adapter(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _async_resolver(None)):
            result = runner.invoke(fb_cli, ["scaffold", "my_comp"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_scaffold_resolver_error(self, runner, fb_cli):
        bad = MagicMock()
        bad.resolve = AsyncMock(side_effect=Exception("adapter error"))
        with patch("oneiric.core.resolution.Resolver", MagicMock(return_value=bad)):
            result = runner.invoke(fb_cli, ["scaffold", "my_comp"])
        assert result.exit_code == 0
        assert "Error" in result.output

    def test_scaffold_success_with_props_and_htmx(self, runner, fb_cli):
        mock_htmy = MagicMock()
        mock_htmy.scaffold_component = AsyncMock(return_value="/path/to/my_comp.py")
        with patch("oneiric.core.resolution.Resolver", _async_resolver(mock_htmy)):
            result = runner.invoke(
                fb_cli,
                [
                    "scaffold", "my_comp",
                    "--type", "dataclass",
                    "--props", "name:str,count:int",
                    "--children", "child_a,child_b",
                    "--htmx",
                    "--endpoint", "/api/my_comp",
                ],
            )
        assert result.exit_code == 0
        mock_htmy.scaffold_component.assert_called_once()


@pytest.mark.unit
class TestListCommand:
    def test_list_no_htmy_adapter(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _async_resolver(None)):
            result = runner.invoke(fb_cli, ["list"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_list_no_components_found(self, runner, fb_cli):
        mock_htmy = MagicMock()
        mock_htmy.discover_components = AsyncMock(return_value={})
        with patch("oneiric.core.resolution.Resolver", _async_resolver(mock_htmy)):
            result = runner.invoke(fb_cli, ["list"])
        assert result.exit_code == 0
        assert "No components found" in result.output

    def test_list_components_displayed(self, runner, fb_cli):
        meta = MagicMock()
        meta.status.value = "ready"
        meta.type.value = "dataclass"
        meta.path = "/app/comps/my_comp.py"
        meta.error_message = None
        meta.docstring = "A test component."
        mock_htmy = MagicMock()
        mock_htmy.discover_components = AsyncMock(return_value={"my_comp": meta})
        with patch("oneiric.core.resolution.Resolver", _async_resolver(mock_htmy)):
            result = runner.invoke(fb_cli, ["list"])
        assert result.exit_code == 0
        assert "my_comp" in result.output

    def test_list_resolver_error(self, runner, fb_cli):
        bad = MagicMock()
        bad.resolve = AsyncMock(side_effect=RuntimeError("discovery failed"))
        with patch("oneiric.core.resolution.Resolver", MagicMock(return_value=bad)):
            result = runner.invoke(fb_cli, ["list"])
        assert result.exit_code == 0
        assert "Error" in result.output


@pytest.mark.unit
class TestValidateCommand:
    def test_validate_no_htmy_adapter(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _async_resolver(None)):
            result = runner.invoke(fb_cli, ["validate", "my_comp"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_validate_success_displays_metadata(self, runner, fb_cli):
        meta = MagicMock()
        meta.type.value = "dataclass"
        meta.status.value = "ready"
        meta.path = "/app/comps/my_comp.py"
        meta.last_modified = None
        meta.docstring = None
        meta.htmx_attributes = {}
        meta.dependencies = []
        meta.error_message = None
        mock_htmy = MagicMock()
        mock_htmy.validate_component = AsyncMock(return_value=meta)
        with patch("oneiric.core.resolution.Resolver", _async_resolver(mock_htmy)):
            result = runner.invoke(fb_cli, ["validate", "my_comp"])
        assert result.exit_code == 0
        assert "dataclass" in result.output

    def test_validate_with_htmx_attributes(self, runner, fb_cli):
        meta = MagicMock()
        meta.type.value = "htmx"
        meta.status.value = "ready"
        meta.path = "/app/comps/my_comp.py"
        meta.last_modified = None
        meta.docstring = "HTMX component"
        meta.htmx_attributes = {"hx-get": "/api/items"}
        meta.dependencies = ["base_comp"]
        meta.error_message = None
        mock_htmy = MagicMock()
        mock_htmy.validate_component = AsyncMock(return_value=meta)
        with patch("oneiric.core.resolution.Resolver", _async_resolver(mock_htmy)):
            result = runner.invoke(fb_cli, ["validate", "my_comp"])
        assert result.exit_code == 0
        assert "hx-get" in result.output

    def test_validate_error_status(self, runner, fb_cli):
        meta = MagicMock()
        meta.type.value = "dataclass"
        meta.status.value = "error"
        meta.path = "/app/comps/my_comp.py"
        meta.last_modified = None
        meta.docstring = None
        meta.htmx_attributes = {}
        meta.dependencies = []
        meta.error_message = "Syntax error on line 5"
        mock_htmy = MagicMock()
        mock_htmy.validate_component = AsyncMock(return_value=meta)
        with patch("oneiric.core.resolution.Resolver", _async_resolver(mock_htmy)):
            result = runner.invoke(fb_cli, ["validate", "my_comp"])
        assert result.exit_code == 0
        assert "Syntax error" in result.output


@pytest.mark.unit
class TestInfoCommand:
    def test_info_no_htmy_adapter(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _async_resolver(None)):
            result = runner.invoke(fb_cli, ["info", "my_comp"])
        assert result.exit_code == 0
        assert "not found" in result.output.lower()

    def test_info_class_load_failure_still_shows_metadata(self, runner, fb_cli):
        meta = MagicMock()
        meta.type.value = "dataclass"
        meta.status.value = "ready"
        meta.path = "/app/comps/my_comp.py"
        mock_htmy = MagicMock()
        mock_htmy.validate_component = AsyncMock(return_value=meta)
        mock_htmy.get_component_class = AsyncMock(side_effect=RuntimeError("no class"))
        with patch("oneiric.core.resolution.Resolver", _async_resolver(mock_htmy)):
            result = runner.invoke(fb_cli, ["info", "my_comp"])
        assert result.exit_code == 0
        assert "dataclass" in result.output

    def test_info_resolver_error(self, runner, fb_cli):
        bad = MagicMock()
        bad.resolve = AsyncMock(side_effect=RuntimeError("resolver down"))
        with patch("oneiric.core.resolution.Resolver", MagicMock(return_value=bad)):
            result = runner.invoke(fb_cli, ["info", "my_comp"])
        assert result.exit_code == 0
        assert "Error" in result.output


@pytest.mark.unit
class TestGenerateIdeConfigCommand:
    def test_vscode_config_generated(self, runner, fb_cli, tmp_path):
        output = str(tmp_path / "vscode_out")
        with patch("fastblocks.cli._generate_vscode_config") as mock_gen:
            result = runner.invoke(fb_cli, ["generate-ide-config", "--output", output])
        assert result.exit_code == 0
        mock_gen.assert_called_once()

    def test_vim_grammar_generated(self, runner, fb_cli, tmp_path):
        output = str(tmp_path / "vim_out")
        with patch("fastblocks.cli._write_static_grammar") as mock_write:
            result = runner.invoke(
                fb_cli, ["generate-ide-config", "--output", output, "--ide", "vim"]
            )
        assert result.exit_code == 0
        mock_write.assert_called_once()

    def test_emacs_grammar_generated(self, runner, fb_cli, tmp_path):
        output = str(tmp_path / "emacs_out")
        with patch("fastblocks.cli._write_static_grammar") as mock_write:
            result = runner.invoke(
                fb_cli, ["generate-ide-config", "--output", output, "--ide", "emacs"]
            )
        assert result.exit_code == 0
        mock_write.assert_called_once()

    def test_unsupported_ide_shows_error_message(self, runner, fb_cli, tmp_path):
        output = str(tmp_path / "unsupported_out")
        result = runner.invoke(
            fb_cli, ["generate-ide-config", "--output", output, "--ide", "notepad"]
        )
        assert result.exit_code == 0
        assert "Unsupported IDE" in result.output


@pytest.mark.unit
class TestSyntaxCheckCommand:
    def test_syntax_check_no_support(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _async_resolver(None)):
            result = runner.invoke(fb_cli, ["syntax-check", "some_template.html"])
        assert result.exit_code == 0
        assert "not available" in result.output.lower()

    def test_syntax_check_resolver_error(self, runner, fb_cli):
        bad = MagicMock()
        bad.resolve = AsyncMock(side_effect=RuntimeError("resolver error"))
        with patch("oneiric.core.resolution.Resolver", MagicMock(return_value=bad)):
            result = runner.invoke(fb_cli, ["syntax-check", "some_template.html"])
        assert result.exit_code == 0
        assert "Error" in result.output


@pytest.mark.unit
class TestFormatTemplateCommand:
    def test_format_template_no_support(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _async_resolver(None)):
            result = runner.invoke(fb_cli, ["format-template", "some_template.html"])
        assert result.exit_code == 0
        assert "not available" in result.output.lower()

    def test_format_template_resolver_error(self, runner, fb_cli):
        bad = MagicMock()
        bad.resolve = AsyncMock(side_effect=RuntimeError("resolver error"))
        with patch("oneiric.core.resolution.Resolver", MagicMock(return_value=bad)):
            result = runner.invoke(fb_cli, ["format-template", "some_template.html"])
        assert result.exit_code == 0
        assert "Error" in result.output


@pytest.mark.unit
class TestStartLanguageServerCommand:
    def test_start_language_server_no_server(self, runner, fb_cli):
        with patch("oneiric.core.resolution.Resolver", _async_resolver(None)):
            result = runner.invoke(fb_cli, ["start-language-server"])
        assert result.exit_code == 0
        assert "not available" in result.output.lower()

    def test_start_language_server_resolver_error(self, runner, fb_cli):
        bad = MagicMock()
        bad.resolve = AsyncMock(side_effect=RuntimeError("resolver error"))
        with patch("oneiric.core.resolution.Resolver", MagicMock(return_value=bad)):
            result = runner.invoke(fb_cli, ["start-language-server"])
        assert result.exit_code == 0
        assert "Error" in result.output


@pytest.mark.unit
class TestCreateSubcommands:
    def test_create_template_makes_directories(self, runner, fb_cli, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        result = runner.invoke(fb_cli, ["create", "template", "--style", "bulma"])
        assert result.exit_code == 0
        assert "Template skeleton created" in result.output

    def test_create_ide_config_delegates_to_generate(self, runner, fb_cli, tmp_path):
        output = str(tmp_path / "ide")
        with patch("fastblocks.cli._generate_vscode_config") as mock_gen:
            result = runner.invoke(fb_cli, ["create", "ide-config", "--output", output])
        assert result.exit_code == 0
        mock_gen.assert_called_once()


@pytest.mark.unit
class TestMcpCommand:
    def test_mcp_import_error_reported(self, runner, fb_cli):
        with patch.dict(sys.modules, {"fastblocks.mcp": None}):
            result = runner.invoke(fb_cli, ["mcp"])
        assert result.exit_code == 0
        assert "not available" in result.output.lower()

    def test_mcp_server_start_exception_reported(self, runner, fb_cli):
        mock_server = MagicMock()
        mock_server.start = AsyncMock(side_effect=Exception("server error"))
        mock_mod = MagicMock()
        mock_mod.create_fastblocks_mcp_server = AsyncMock(return_value=mock_server)
        with patch.dict(sys.modules, {"fastblocks.mcp": mock_mod}):
            result = runner.invoke(fb_cli, ["mcp"])
        assert result.exit_code == 0
        assert "Error" in result.output
