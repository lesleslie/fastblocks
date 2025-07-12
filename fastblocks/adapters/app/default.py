import typing as t
from base64 import b64encode
from contextlib import asynccontextmanager, suppress
from time import perf_counter

from acb.adapters import get_adapter, import_adapter
from acb.depends import depends
from starlette.types import ASGIApp, Receive, Scope, Send
from fastblocks.applications import FastBlocks

from ._base import AppBase, AppBaseSettings

main_start = perf_counter()

try:
    Cache, Storage = import_adapter()
except Exception:
    Cache = Storage = None


class AppSettings(AppBaseSettings):
    url: str = "http://localhost:8000"
    token_id: str | None = "_fb_"

    def __init__(self, **data: t.Any) -> None:
        super().__init__(**data)
        with suppress(Exception):
            config = depends.get("config")
            self.url = self.url if not config.deployed else f"https://{self.domain}"
        token_prefix = self.token_id or "_fb_"
        self.token_id = "".join(
            [token_prefix, b64encode(self.name.encode()).decode().rstrip("=")],
        )


class FastBlocksApp(FastBlocks):
    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(lifespan=self.lifespan, **kwargs)

    async def init(self) -> None:
        pass

    def _get_startup_time(self) -> float:
        startup_time = getattr(self, "_startup_time", None)
        if startup_time is None or startup_time <= 0:
            import time

            init_start = getattr(self, "_init_start_time", None)
            startup_time = time.time() - init_start if init_start else 0.001
        return startup_time

    def _get_debug_enabled(self, config: t.Any) -> list[str]:
        debug_enabled = []
        if hasattr(config, "debug"):
            for key, value in vars(config.debug).items():
                if value and key != "production":
                    debug_enabled.append(key)
        return debug_enabled

    def _get_color_constants(self) -> dict[str, str]:
        return {
            "GREEN": "\033[92m",
            "BLUE": "\033[94m",
            "YELLOW": "\033[93m",
            "CYAN": "\033[96m",
            "RESET": "\033[0m",
            "BOLD": "\033[1m",
        }

    def _format_info_lines(
        self,
        config: t.Any,
        colors: dict[str, str],
        debug_enabled: list[str],
        startup_time: float,
    ) -> list[str]:
        app_title = getattr(config.app, "title", "Welcome to FastBlocks")
        app_domain = getattr(config.app, "domain", "localhost")
        debug_str = ", ".join(debug_enabled) if debug_enabled else "disabled"

        return [
            f"{colors['CYAN']}{colors['BOLD']}{app_title}{colors['RESET']}",
            f"{colors['BLUE']}Domain: {app_domain}{colors['RESET']}",
            f"{colors['YELLOW']}Debug: {debug_str}{colors['RESET']}",
            f"{colors['YELLOW']}══════════════════════════════════════════════════{colors['RESET']}",
            f"{colors['GREEN']}🚀 FastBlocks Application Ready{colors['RESET']}",
            f"{colors['YELLOW']}⚡ Startup time: {startup_time * 1000:.2f}ms{colors['RESET']}",
            f"{colors['CYAN']}🌐 Server running on http://127.0.0.1:8000{colors['RESET']}",
            f"{colors['YELLOW']}══════════════════════════════════════════════════{colors['RESET']}",
        ]

    def _clean_and_center_line(self, line: str, colors: dict[str, str]) -> str:
        line_clean = line
        for color in colors.values():
            line_clean = line_clean.replace(color, "")
        line_width = len(line_clean)
        padding = max(0, (90 - line_width) // 2)
        return " " * padding + line

    async def _display_fancy_startup(self) -> None:
        from acb.depends import depends
        from aioconsole import aprint
        from pyfiglet import Figlet

        config = depends.get("config")
        app_name = getattr(config.app, "name", "FastBlocks")
        startup_time = self._get_startup_time()
        debug_enabled = self._get_debug_enabled(config)
        colors = self._get_color_constants()
        banner = Figlet(font="slant", width=90, justify="center").renderText(
            app_name.upper(),
        )
        await aprint(f"\n\n{banner}\n")
        info_lines = self._format_info_lines(
            config,
            colors,
            debug_enabled,
            startup_time,
        )
        for line in info_lines:
            self._clean_and_center_line(line, colors)

    def _display_simple_startup(self) -> None:
        from contextlib import suppress

        with suppress(Exception):
            from acb.depends import depends

            config = depends.get("config")
            getattr(config.app, "name", "FastBlocks")
            self._get_startup_time()

    async def post_startup(self) -> None:
        try:
            await self._display_fancy_startup()
        except Exception:
            self._display_simple_startup()

    @asynccontextmanager
    async def lifespan(self, app: "FastBlocks") -> t.AsyncIterator[None]:
        try:
            logger = getattr(self, "logger", None)
            if logger:
                logger.info("FastBlocks application starting up")
        except Exception as e:
            logger = getattr(self, "logger", None)
            if logger:
                logger.exception(f"Error during startup: {e}")
            raise
        yield
        logger = getattr(self, "logger", None)
        if logger:
            logger.info("FastBlocks application shutting down")


class App(AppBase):
    settings: AppSettings | None = None
    router: t.Any = None
    middleware_manager: t.Any = None
    templates: t.Any = None
    models: t.Any = None
    exception_handlers: t.Any = None
    middleware_stack: t.Any = None
    user_middleware: t.Any = None
    fastblocks_app: t.Any = None

    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        self.settings = AppSettings()
        self.fastblocks_app = FastBlocksApp()
        self.router = None
        self.middleware_manager = None
        self.templates = None
        self.models = None
        self.exception_handlers = {}
        self.middleware_stack = None
        self.user_middleware = []
        self.state = None

    @property
    def logger(self) -> t.Any:
        if hasattr(super(), "logger"):
            with suppress(Exception):
                return super().logger
        try:
            return depends.get("logger")
        except Exception:
            import logging

            return logging.getLogger(self.__class__.__name__)

    @logger.setter
    def logger(self, value: t.Any) -> None:
        pass

    @logger.deleter
    def logger(self) -> None:
        pass

    async def init(self) -> None:
        import time

        self._init_start_time = time.time()
        await self.fastblocks_app.init()
        try:
            self.templates = depends.get("templates")
        except Exception:
            self.templates = None
        try:
            self.models = depends.get("models")
        except Exception:
            self.models = None
        try:
            routes_adapter = depends.get("routes")
            self.router = routes_adapter
            self.fastblocks_app.routes.extend(routes_adapter.routes)
        except Exception:
            self.router = None
        self.middleware_manager = None
        self.exception_handlers = self.fastblocks_app.exception_handlers
        self.middleware_stack = self.fastblocks_app.middleware_stack
        self.user_middleware = self.fastblocks_app.user_middleware
        self.state = self.fastblocks_app.state
        import time

        self._startup_time = time.time() - self._init_start_time
        self.fastblocks_app._startup_time = self._startup_time
        self.fastblocks_app._init_start_time = self._init_start_time
        await self.post_startup()

    def __call__(self, scope: Scope, receive: Receive, send: Send) -> ASGIApp:
        return self.fastblocks_app(scope, receive, send)

    def __getattr__(self, name: str):
        return getattr(self.fastblocks_app, name)

    async def post_startup(self) -> None:
        await self.fastblocks_app.post_startup()

    def _setup_admin_adapter(self, app: FastBlocks) -> None:
        if not get_adapter("admin"):
            return
        sql = depends.get("sql")
        auth = depends.get("auth")
        admin = depends.get("admin")
        admin.__init__(
            app,
            engine=sql.engine,
            title=self.config.admin.title,
            debug=getattr(self.config.debug, "admin", False),
            base_url=self.config.admin.url,
            logo_url=self.config.admin.logo_url,
            authentication_backend=auth,
        )
        self.router.routes.insert(0, self.router.routes.pop())

    async def _startup_sequence(self, app: FastBlocks) -> None:
        self._setup_admin_adapter(app)
        await self.post_startup()
        main_start_time = perf_counter() - main_start
        self.logger.warning(f"App started in {main_start_time} s")

    async def _shutdown_logger(self) -> None:
        import asyncio

        completer = None
        if hasattr(self.logger, "complete"):
            completer = self.logger.complete()
        elif hasattr(self.logger, "stop"):
            completer = self.logger.stop()
        if completer:
            await asyncio.wait_for(completer, timeout=1.0)

    def _cancel_remaining_tasks(self) -> None:
        import asyncio

        loop = asyncio.get_event_loop()
        tasks = [t for t in asyncio.all_tasks(loop) if not t.done()]
        if tasks:
            self.logger.debug(f"Cancelling {len(tasks)} remaining tasks")
            for task in tasks:
                task.cancel()

    @asynccontextmanager
    async def lifespan(self, app: FastBlocks) -> t.AsyncIterator[None]:
        try:
            await self._startup_sequence(app)
        except Exception as e:
            self.logger.exception(f"Error during startup: {e}")
            raise
        yield
        self.logger.critical("Application shut down")
        try:
            await self._shutdown_logger()
        except TimeoutError:
            self.logger.warning("Logger completion timed out, forcing shutdown")
        except Exception as e:
            self.logger.exception(f"Logger completion failed: {e}")
        finally:
            with suppress(Exception):
                self._cancel_remaining_tasks()
