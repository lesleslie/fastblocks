"""Tests for the FastBlocks templates base module."""

from unittest.mock import MagicMock

import pytest
from fastblocks.adapters.templates._base import (
    TemplatesBaseSettings,
    safe_await,
)


class TestSafeAwait:
    @pytest.mark.asyncio
    async def test_safe_await_with_awaitable(self) -> None:
        """Test safe_await with an awaitable."""

        # Create an awaitable
        async def awaitable() -> str:
            return "result"

        # Call safe_await
        result = await safe_await(awaitable)

        # Verify the result
        assert result == "result"

    @pytest.mark.asyncio
    async def test_safe_await_with_callable(self) -> None:
        """Test safe_await with a callable."""

        # Create a callable
        def callable() -> str:
            return "result"

        # Call safe_await
        result = await safe_await(callable)

        # Verify the result
        assert result == "result"

    @pytest.mark.asyncio
    async def test_safe_await_with_value(self) -> None:
        """Test safe_await with a value."""
        # Call safe_await
        result = await safe_await("result")

        # Verify the result
        assert result == "result"

    @pytest.mark.asyncio
    async def test_safe_await_with_exception(self) -> None:
        """Test safe_await with a callable that raises an exception."""

        # Create a callable that raises an exception
        def callable() -> None:
            raise ValueError("error")

        # Call safe_await
        result = await safe_await(callable)

        # Verify the result
        assert result is True


class TestTemplatesBaseSettings:
    def test_templates_base_settings_init_deployed(self) -> None:
        """Test TemplatesBaseSettings initialization with deployed config."""
        # Create a mock config
        mock_config = MagicMock()
        mock_config.deployed = True

        # Create settings
        settings = TemplatesBaseSettings(config=mock_config, cache_timeout=300)

        # Verify the settings
        assert settings.cache_timeout == 300

    def test_templates_base_settings_init_not_deployed(self) -> None:
        """Test TemplatesBaseSettings initialization with non-deployed config."""
        # Create a mock config
        mock_config = MagicMock()
        mock_config.deployed = False

        # Create settings
        settings = TemplatesBaseSettings(config=mock_config, cache_timeout=300)

        # Verify the settings
        assert settings.cache_timeout == 1
