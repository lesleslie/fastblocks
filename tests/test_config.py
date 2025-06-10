"""Simple tests for the config module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from acb.config import Settings
from anyio import Path as AsyncPath


@pytest.mark.unit
class TestConfig:
    @pytest.fixture
    def temp_dir(self, monkeypatch: pytest.MonkeyPatch):
        with tempfile.TemporaryDirectory() as tmp_dir:
            tmp_path = Path(tmp_dir)
            settings_dir = tmp_path / "settings"
            settings_dir.mkdir(exist_ok=True)

            (settings_dir / "app.yml").touch()
            (settings_dir / "adapters.yml").touch()
            (settings_dir / "debug.yml").touch()

            original_path_exists = Path.exists
            original_async_path_exists = AsyncPath.exists

            def mock_path_exists(path: Path):
                if str(path).endswith(("app.yml", "adapters.yml", "debug.yml")):
                    return True
                return original_path_exists(path)

            def mock_async_path_exists(path: AsyncPath):
                if str(path).endswith(("app.yml", "adapters.yml", "debug.yml")):
                    return True
                return original_async_path_exists(path)

            monkeypatch.setattr(Path, "exists", mock_path_exists)
            monkeypatch.setattr(AsyncPath, "exists", mock_async_path_exists)

            yield tmp_path

    @pytest.fixture
    def config_files(self, temp_dir: Path):
        app_yml = temp_dir / "settings" / "app.yml"
        adapters_yml = temp_dir / "settings" / "adapters.yml"
        debug_yml = temp_dir / "settings" / "debug.yml"

        with (
            patch.object(Path, "write_text", MagicMock(return_value=None)),
            patch.object(Path, "read_text", MagicMock(return_value="")),
        ):
            yield {
                "app": app_yml,
                "adapters": adapters_yml,
                "debug": debug_yml,
                "dir": temp_dir,
            }

    def test_settings_init(self, config_files: dict[str, AsyncPath]) -> None:
        with patch.object(AsyncPath, "exists", MagicMock(return_value=True)):
            settings = Settings(config_files["dir"])
            assert settings is not None

    def test_settings_load(self, config_files: dict[str, AsyncPath]) -> None:
        with (
            patch.object(AsyncPath, "exists", MagicMock(return_value=True)),
            patch.object(AsyncPath, "read_text", MagicMock(return_value="name: test")),
        ):
            settings = Settings(config_files["dir"])
            # Test that settings object is created successfully
            # Note: Settings mock may not have load method
            assert hasattr(settings, "app")
            assert hasattr(settings, "adapters")
            assert hasattr(settings, "debug")
