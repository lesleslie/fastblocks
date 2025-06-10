import typing as t
from base64 import b64encode
from contextlib import asynccontextmanager
from time import perf_counter

from acb.adapters import get_adapter, import_adapter
from acb.config import Config
from acb.depends import depends
from fastblocks.applications import FastBlocks

from ._base import AppBase, AppBaseSettings

main_start = perf_counter()
Cache, Storage = import_adapter()


class AppSettings(AppBaseSettings):
    url: str = "http://localhost:8000"
    token_id: str | None = "_fb_"

    @depends.inject
    def __init__(self, config: Config = depends(), **data: t.Any) -> None:
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
        self.templates = depends.get().app
        self.routes.extend(depends.get("routes").routes)

    async def post_startup(self) -> None:
        if not self.config.deployed:
            from aioconsole import aprint
            from pyfiglet import Figlet

            fig = Figlet(font="slant", width=90, justify="center")
            await aprint(f"\n\n{fig.renderText(self.config.app.name.upper())}\n")
        if not self.config.debug.production and self.config.deployed:
            self.logger.info("Entering production mode...")

    @asynccontextmanager
    async def lifespan(self, app: FastBlocks) -> t.AsyncIterator[None]:
        try:
            if get_adapter("admin"):
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
            await self.post_startup()
            main_start_time = perf_counter() - main_start
            self.logger.warning(f"App started in {main_start_time} s")
        except Exception as e:
            self.logger.error(f"Error during startup: {e}")
            raise e
        yield
        self.logger.critical("Application shut down")
        completer = self.logger.complete()
        await completer


depends.set(App)
