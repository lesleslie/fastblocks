import typing as t
from contextlib import suppress
from pathlib import Path

# Oneiric imports
from oneiric.adapters.bootstrap import (
    register_adapter_metadata,
    register_builtin_adapters,
)
from oneiric.core.resolution import Resolver, register_pkg

# Create resolver instance for dependency resolution
_resolver = Resolver()


async def _get_dependency(name: str) -> t.Any:
    """Get dependency using Oneiric resolver."""
    return await _resolver.resolve(name)


# Use Path(__file__).parent.parent as root_path
root_path = Path(__file__).parent.parent

_app_instance = None
_logger_instance = None


def _check_dev_mode() -> None:
    """Check if running in development mode and raise error if so."""
    current_dir = Path.cwd()
    fastblocks_pkg_dir = Path(__file__).parent
    fastblocks_root_dir = fastblocks_pkg_dir.parent
    is_dev_mode = current_dir == fastblocks_pkg_dir or (
        current_dir == fastblocks_root_dir and (current_dir / "pyproject.toml").exists()
    )
    if is_dev_mode:
        msg = (
            "FastBlocks cannot be run from its own package directory. "
            "Please run from your application directory."
        )
        raise RuntimeError(
            msg,
        )


async def _handle_registration() -> None:
    """Handle adapter registration using Oneiric."""
    # Oneiric: Register builtin adapters
    try:
        await register_builtin_adapters()
    except Exception as e:
        msg = f"Failed to register builtin adapters: {e}"
        raise RuntimeError(msg) from e


async def _handle_adapter_registration() -> None:
    """Handle adapter registration using Oneiric."""
    # Oneiric: Register adapter metadata
    with suppress(Exception):
        await register_adapter_metadata(root_path)


async def _get_app_instance() -> t.Any:
    """Get the app instance."""
    try:
        return await _get_dependency("app")
    except Exception as e:
        msg = f"Failed to get app adapter: {e}. Make sure adapters are properly registered and configured."
        raise RuntimeError(
            msg,
        ) from e


async def _get_logger_instance() -> t.Any:
    """Get the logger instance."""
    try:
        return await _get_dependency("logger")
    except Exception as e:
        import logging

        logger_instance = logging.getLogger("fastblocks")
        logger_instance.warning(
            f"Failed to get logger adapter, using fallback: {e}",
        )
        return logger_instance


async def get_app() -> t.Any:
    global _app_instance, _logger_instance
    if _app_instance is None:
        _check_dev_mode()

        try:
            register_pkg()
        except Exception as e:
            msg = f"Failed to register FastBlocks adapters: {e}"
            raise RuntimeError(msg) from e

        await _handle_registration()
        await _handle_adapter_registration()

        _app_instance = await _get_app_instance()
        _logger_instance = await _get_logger_instance()

    return _app_instance


def get_logger() -> t.Any:
    return _logger_instance


class LazyApp:
    def __getattr__(self, name: str) -> t.Any:
        if _app_instance is None:
            msg = "FastBlocks app has not finished initializing"
            raise AttributeError(msg)
        return getattr(_app_instance, name)

    async def __call__(self, scope: t.Any, receive: t.Any, send: t.Any) -> None:
        app = await get_app()
        await app(scope, receive, send)


class LazyLogger:
    def __getattr__(self, name: str) -> t.Any:
        if _logger_instance is None:
            msg = "FastBlocks logger has not finished initializing"
            raise AttributeError(msg)
        return getattr(_logger_instance, name)

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        logger = _logger_instance
        if callable(logger):
            return logger(*args, **kwargs)
        return logger


app = LazyApp()
logger = LazyLogger()
