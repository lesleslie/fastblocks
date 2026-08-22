"""fastblocks settings loader tests (Phase 2.5 Commit2)."""

from __future__ import annotations

from pathlib import Path

import pytest
import yaml
from fastblocks.core.settings_loader import (
    load_fastblocks_settings,
)


class TestLoadFastblocksSettings:
    @pytest.mark.unit
    def test_loader_returns_app_settings_with_yaml_fields(
        self, tmp_path: Path
    ) -> None:
        """Happy path: yaml file at tmp_path, fields populate AppSettings."""
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text(
            "title: 'Test App'\n"
            "domain: 'example.com'\n"
            "style: 'vanilla'\n"
            "version: '1.0.0'\n"
        )
        s = load_fastblocks_settings(path=str(yaml_path))
        assert s.title == "Test App"
        assert s.domain == "example.com"
        assert s.style == "vanilla"
        assert s.version == "1.0.0"

    @pytest.mark.unit
    def test_loader_raises_filenotfound_when_no_yaml(
        self, tmp_path: Path
    ) -> None:
        """No yaml at any path → FileNotFoundError."""
        with pytest.raises(FileNotFoundError):
            load_fastblocks_settings(path=str(tmp_path / "nonexistent.yml"))

    @pytest.mark.unit
    def test_loader_propagates_yaml_error(self, tmp_path: Path) -> None:
        """Malformed YAML propagates yaml.YAMLError."""
        bad_yaml = tmp_path / "bad.yml"
        bad_yaml.write_text("title: 'unclosed\ndomain: 'x'\n")
        with pytest.raises(yaml.YAMLError):
            load_fastblocks_settings(path=str(bad_yaml))

    @pytest.mark.unit
    def test_loader_rejects_invalid_literal_via_pydantic(
        self, tmp_path: Path
    ) -> None:
        """YAML with style: 'kelp' triggers Pydantic ValidationError (Literal)."""
        from pydantic import ValidationError

        bad_yaml = tmp_path / "kelp.yml"
        bad_yaml.write_text("style: 'kelp'\n")
        with pytest.raises(ValidationError):
            load_fastblocks_settings(path=str(bad_yaml))

    @pytest.mark.unit
    def test_loader_ignores_extra_yaml_fields(
        self, tmp_path: Path
    ) -> None:
        """Unknown YAML fields are silently dropped (extra='ignore')."""
        yaml_path = tmp_path / "extra.yml"
        yaml_path.write_text("style: 'vanilla'\nunknown_field: 'x'\n")
        s = load_fastblocks_settings(path=str(yaml_path))
        assert s.style == "vanilla"

    @pytest.mark.unit
    def test_loader_falls_back_to_defaults_when_yaml_empty(
        self, tmp_path: Path
    ) -> None:
        """Empty YAML file → AppSettings with all defaults."""
        yaml_path = tmp_path / "empty.yml"
        yaml_path.write_text("")
        s = load_fastblocks_settings(path=str(yaml_path))
        assert s.style == "fastblocks_ui"  # DEFAULT_STYLE
        assert s.title == ""
