import typing as t
from contextlib import asynccontextmanager
from time import perf_counter

from acb.adapters import get_adapter, import_adapter
from acb.config import Config
from acb.depends import depends
from fastblocks.applications import FastBlocks

from ._base import AppBase, AppBaseSettings

main_start = perf_counter()

Auth, Monitoring, Storage, Sql = import_adapter()  # type: ignore


class AppSettings(AppBaseSettings):
    url: str = "http://localhost:8000"

    @depends.inject
    def __init__(self, config: Config = depends(), **data: t.Any) -> None:
        super().__init__(**data)
        self.url = self.url if not config.deployed else f"https://{self.domain}"


class App(FastBlocks, AppBase):
    def __init__(self) -> None:
        super().__init__(lifespan=self.lifespan)

    async def init(self) -> None:
        self.templates = depends.get().app
        self.routes.extend(depends.get("routes").routes)

    @asynccontextmanager
    @depends.inject
    async def lifespan(  # type: ignore
        self,
        app: FastBlocks,
        auth: Auth = depends(),
        sql: Sql = depends(),
    ) -> t.Any:
        if get_adapter("admin").enabled:
            admin = depends.get()
            admin.__init__(
                app,
                engine=sql.engine,
                title=self.config.admin.title,
                debug=self.config.debug.admin,
                base_url=self.config.admin.url,
                logo_url=self.config.admin.logo_url,
                authentication_backend=auth,
            )
            self.router.routes.insert(0, self.router.routes.pop())

        async def post_startup() -> None:
            if not self.config.deployed:
                from aioconsole import aprint
                from pyfiglet import Figlet

                fig = Figlet(font="slant", width=90, justify="center")
                await aprint(f"\n\n{fig.renderText(self.config.app.name.upper())}\n")
            if not self.config.debug.production and self.config.deployed:
                self.logger.info("Entering production mode...")

        await post_startup()
        main_start_time = perf_counter() - main_start
        self.logger.warning(f"App started in {main_start_time} s")
        yield
        self.logger.critical("Application shut down")
        await self.logger.complete()


depends.set(App)
