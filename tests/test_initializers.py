from types import SimpleNamespace
from unittest.mock import MagicMock, patch

import pytest

from fastblocks.initializers import ApplicationInitializer


@pytest.mark.unit
class TestInitializerErrorHandling:
    def test_installs_error_handler_in_dev(self) -> None:
        config = SimpleNamespace(
            deployed=False,
            debug=SimpleNamespace(production=False),
        )
        initializer = ApplicationInitializer(MagicMock(), config=config)
        initializer.config = config

        with patch("fastblocks.initializers.install_error_handler") as install:
            initializer._configure_error_handling()
            install.assert_called_once()

    def test_skips_error_handler_in_prod(self) -> None:
        config = SimpleNamespace(
            deployed=True,
            debug=SimpleNamespace(production=False),
        )
        initializer = ApplicationInitializer(MagicMock(), config=config)
        initializer.config = config

        with patch("fastblocks.initializers.install_error_handler") as install:
            initializer._configure_error_handling()
            install.assert_not_called()

    def test_skips_error_handler_in_debug_production(self) -> None:
        config = SimpleNamespace(
            deployed=False,
            debug=SimpleNamespace(production=True),
        )
        initializer = ApplicationInitializer(MagicMock(), config=config)
        initializer.config = config

        with patch("fastblocks.initializers.install_error_handler") as install:
            initializer._configure_error_handling()
            install.assert_not_called()

    def test_fastblocks_init_skips_error_handler_in_prod(self) -> None:
        from fastblocks.applications import FastBlocks

        config = SimpleNamespace(
            deployed=True,
            debug=SimpleNamespace(production=False, fastblocks=False),
            app=SimpleNamespace(secret_key=SimpleNamespace(get_secret_value=lambda: "x")),
        )

        with patch("fastblocks.initializers.install_error_handler") as install:
            FastBlocks(config=config)
            install.assert_not_called()
