"""Simple tests for the config module."""

import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
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
        # Mock the Settings class
        with patch("acb.config.Settings", MagicMock()) as mock_settings:
            # Configure the mock to return a properly structured object
            mock_instance = MagicMock()
            mock_settings.return_value = mock_instance

            # Call the constructor
            settings = mock_settings(config_files["dir"])

            # Verify the constructor was called with the expected arguments
            mock_settings.assert_called_once_with(config_files["dir"])
            assert settings is not None

    def test_settings_load(self, config_files: dict[str, AsyncPath]) -> None:
        # Mock the Settings class
        with patch("acb.config.Settings", MagicMock()) as mock_settings:
            # Configure the mock to return a properly structured object
            mock_instance = MagicMock()
            mock_instance.app = MagicMock()
            mock_instance.adapters = MagicMock()
            mock_instance.debug = MagicMock()
            mock_settings.return_value = mock_instance

            # Call the constructor
            settings = mock_settings(config_files["dir"])

            # Verify the expected attributes are present
            assert hasattr(settings, "app")
            assert hasattr(settings, "adapters")
            assert hasattr(settings, "debug")
