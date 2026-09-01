"""Tests for fastblocks/cli.py IDE-config generation.

Targets the uncovered ``_generate_vscode_config`` and
``_write_static_grammar`` helpers in fastblocks/cli.py (132 missing
statements before this file).
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from fastblocks.cli import _generate_vscode_config, _write_static_grammar


@pytest.mark.unit
class TestGenerateVSCodeConfig:
    def test_writes_all_four_files(self, tmp_path: Path) -> None:
        _generate_vscode_config(tmp_path)
        # 4 files should be written.
        assert (tmp_path / "package.json").exists()
        assert (tmp_path / "language-configuration.json").exists()
        assert (tmp_path / "syntaxes" / "fastblocks.tmLanguage.json").exists()
        assert (tmp_path / "settings.json").exists()

    def test_package_json_is_valid_json(self, tmp_path: Path) -> None:
        _generate_vscode_config(tmp_path)
        pkg = json.loads((tmp_path / "package.json").read_text())
        assert isinstance(pkg, dict)
        # Standard VS Code manifest fields.
        assert "name" in pkg or "contributes" in pkg

    def test_settings_json_is_valid_json(self, tmp_path: Path) -> None:
        _generate_vscode_config(tmp_path)
        settings = json.loads((tmp_path / "settings.json").read_text())
        assert isinstance(settings, dict)
        assert settings["fastblocks.languageServer.enabled"] is True


@pytest.mark.unit
class TestWriteStaticGrammar:
    def test_vim_grammar_writes_file(self, tmp_path: Path) -> None:
        _write_static_grammar("vim", tmp_path)
        assert (tmp_path / "fastblocks.vim").exists()

    def test_emacs_grammar_writes_file(self, tmp_path: Path) -> None:
        _write_static_grammar("emacs", tmp_path)
        assert (tmp_path / "fastblocks-mode.el").exists()
