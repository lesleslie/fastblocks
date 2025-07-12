import typing as t
from pathlib import Path

from acb import register_pkg
from acb.depends import depends

_app_instance = None
_logger_instance = None


def get_app():
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
            _app_instance = depends.get("app")
        except Exception as e:
            msg = f"Failed to get app adapter: {e}. Make sure adapters are properly registered and configured."
            raise RuntimeError(
                msg,
            ) from e
        try:
            _logger_instance = depends.get("logger")
        except Exception as e:
            import logging

            _logger_instance = logging.getLogger("fastblocks")
            _logger_instance.warning(
                f"Failed to get logger adapter, using fallback: {e}",
            )
    return _app_instance


def get_logger():
    get_app()
    return _logger_instance


class LazyApp:
    def __getattr__(self, name: str):
        return getattr(get_app(), name)

    async def __call__(self, scope: t.Any, receive: t.Any, send: t.Any) -> None:
        app = get_app()
        await app(scope, receive, send)


class LazyLogger:
    def __getattr__(self, name: str):
        return getattr(get_logger(), name)

    def __call__(self, *args: t.Any, **kwargs: t.Any) -> t.Any:
        logger = get_logger()
        if callable(logger):
            call_method = logger.__call__
            return call_method(*args, **kwargs)
        return logger


app = LazyApp()
logger = LazyLogger()
