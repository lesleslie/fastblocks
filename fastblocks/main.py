import typing as t
from contextlib import suppress
from pathlib import Path

from acb import ensure_registration, register_pkg
from acb.adapters import register_adapters, root_path
from acb.depends import depends

_app_instance = None
_logger_instance = None


async def get_app() -> t.Any:
    global _app_instance, _logger_instance
    if _app_instance is None:
        current_dir = Path.cwd()
        fastblocks_pkg_dir = Path(__file__).parent
        fastblocks_root_dir = fastblocks_pkg_dir.parent
        is_dev_mode = current_dir == fastblocks_pkg_dir or (
            current_dir == fastblocks_root_dir
            and (current_dir / "pyproject.toml").exists()
        )
        if is_dev_mode:
            msg = (
                "FastBlocks cannot be run from its own package directory. "
                "Please run from your application directory."
            )
            raise RuntimeError(
                msg,
            )
        try:
            register_pkg()
        except Exception as e:
            msg = f"Failed to register FastBlocks adapters: {e}"
            raise RuntimeError(msg) from e
        try:
            await ensure_registration()
        except Exception as e:
            msg = f"Failed to register packages: {e}"
            raise RuntimeError(msg) from e
        with suppress(Exception):
            await register_adapters(root_path)
        try:
            _app_instance = await depends.get("app")
        except Exception as e:
            msg = f"Failed to get app adapter: {e}. Make sure adapters are properly registered and configured."
            raise RuntimeError(
                msg,
            ) from e
        try:
            _logger_instance = await depends.get("logger")
        except Exception as e:
            import logging

            _logger_instance = logging.getLogger("fastblocks")
            _logger_instance.warning(
                f"Failed to get logger adapter, using fallback: {e}",
            )
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
