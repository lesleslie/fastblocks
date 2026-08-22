"""AppSettings YAML wiring tests (Phase 2.5 Commit3)."""

from __future__ import annotations

from pathlib import Path

import pytest


class TestAppSettingsYamlWiring:
    @pytest.mark.unit
    def test_app_settings_reads_title_from_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppSettings() picks up title from CWD/app.yml."""
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text("title: 'Wired Title'\n")
        monkeypatch.chdir(tmp_path)
        from fastblocks.adapters.app.default import AppSettings
        s = AppSettings()
        assert s.title == "Wired Title"

    @pytest.mark.unit
    def test_app_settings_soft_fallback_when_no_yaml(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """AppSettings() works with defaults when no app.yml exists anywhere."""
        monkeypatch.chdir(tmp_path)  # empty dir, no app.yml
        from fastblocks.adapters.app.default import AppSettings
        s = AppSettings()
        # Defaults: style="fastblocks_ui", title=""
        assert s.style == "fastblocks_ui"
        assert s.title == ""

    @pytest.mark.unit
    def test_app_settings_rejects_invalid_yaml_style(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """YAML with style='kelp' triggers Pydantic ValidationError."""
        from pydantic import ValidationError
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text("style: 'kelp'\n")
        monkeypatch.chdir(tmp_path)
        from fastblocks.adapters.app.default import AppSettings
        with pytest.raises(ValidationError):
            AppSettings()

    @pytest.mark.unit
    def test_app_settings_round_trip_yaml_to_dump(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """Loaded AppSettings can be dumped back to YAML-compatible dict."""
        yaml_path = tmp_path / "app.yml"
        yaml_path.write_text(
            "title: 'Round Trip'\n"
            "domain: 'rt.example'\n"
            "style: 'vanilla'\n"
        )
        monkeypatch.chdir(tmp_path)
        from fastblocks.adapters.app.default import AppSettings
        s = AppSettings()
        dumped = s.model_dump()
        assert dumped["title"] == "Round Trip"
        assert dumped["domain"] == "rt.example"
        assert dumped["style"] == "vanilla"
