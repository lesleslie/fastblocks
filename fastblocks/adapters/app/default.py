import typing as t
from base64 import b64encode
from contextlib import asynccontextmanager, suppress
from time import perf_counter

from fastblocks.applications import FastBlocks

from ...dependencies import get_acb_subset
from ._base import AppBase, AppBaseSettings

get_adapter, import_adapter, Config, depends = get_acb_subset(
    "get_adapter", "import_adapter", "Config", "depends"
)

main_start = perf_counter()

try:
    Cache, Storage = import_adapter()
except Exception:
    Cache = Storage = None


class AppSettings(AppBaseSettings):
    url: str = "http://localhost:8000"
    token_id: str | None = "_fb_"

    @depends.inject
    def __init__(self, config: t.Any = depends(), **data: t.Any) -> None:
        super().__init__(**data)
        self.url = self.url if not config.deployed else f"https://{self.domain}"
        token_prefix = self.token_id or "_fb_"
        self.token_id = "".join(
            [token_prefix, b64encode(self.name.encode()).decode().rstrip("=")]
        )


class App(FastBlocks, AppBase):
    def __init__(self) -> None:
        super().__init__(lifespan=self.lifespan)

    async def init(self) -> None:
        try:
            templates_adapter = depends.get("templates")
            self.templates = templates_adapter.app
        except Exception:
            self.templates = None
        with suppress(Exception):
            routes_adapter = depends.get("routes")
            self.routes.extend(routes_adapter.routes)

    async def post_startup(self) -> None:
        if not self.config.deployed:
            from aioconsole import aprint
            from pyfiglet import Figlet

            fig = Figlet(font="slant", width=90, justify="center")
            await aprint(f"\n\n{fig.renderText(self.config.app.name.upper())}\n")
        if not self.config.debug.production and self.config.deployed:
            self.logger.info("Entering production mode...")

    def _setup_admin_adapter(self, app: FastBlocks) -> None:
        if not get_adapter("admin"):
            return
        sql = depends.get()
        auth = depends.get()
        admin = depends.get()
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
            completer = getattr(self.logger, "complete")()
        elif hasattr(self.logger, "stop"):
            completer = getattr(self.logger, "stop")()
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
            self.logger.error(f"Error during startup: {e}")
            raise e
        yield
        self.logger.critical("Application shut down")
        try:
            await self._shutdown_logger()
        except TimeoutError:
            self.logger.warning("Logger completion timed out, forcing shutdown")
        except Exception as e:
            self.logger.error(f"Logger completion failed: {e}")
        finally:
            with suppress(Exception):
                self._cancel_remaining_tasks()


with suppress(Exception):
    depends.set(App)
