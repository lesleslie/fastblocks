import typing as t
from contextlib import asynccontextmanager
from time import perf_counter

from acb.adapters import get_adapter
from acb.adapters import import_adapter
from acb.debug import debug
from acb.depends import depends

from fastblocks.applications import FastBlocks
from ._base import AppBase
from ._base import AppBaseSettings

Logger = import_adapter("logger")
Cache = import_adapter("cache")
Storage = import_adapter("storage")
Sql = import_adapter("sql")
Auth = import_adapter("auth")

main_start = perf_counter()


class AppSettings(AppBaseSettings): ...


class App(FastBlocks, AppBase):
    def __init__(self) -> None:
        super().__init__(lifespan=self.lifespan)

    @depends.inject
    async def init(self) -> None:
        self.templates = depends.get(import_adapter("templates")).app
        self.routes.extend(depends.get(import_adapter("routes")).routes)
        # for adapter in get_installed_adapters():
        #     debug(f"**** {adapter.category.upper()} ****")
        #     for k, v in vars(adapter).items():
        #         debug(k, v)
        for route in self.routes:
            debug(route)

    @asynccontextmanager
    @depends.inject
    async def lifespan(
        self,
        app: FastBlocks,
        cache: Cache = depends(),  # type: ignore
        auth: Auth = depends(),  # type: ignore
        sql: Sql = depends(),  # type: ignore
    ) -> t.AsyncGenerator[None, None]:
        if get_adapter("admin").enabled:
            admin = depends.get(import_adapter("admin"))
            admin.__init__(
                app,
                engine=sql.engine,
                title=self.config.admin.title,
                debug=self.config.debug.admin,
                base_url=self.config.admin.url,
                logo_url=self.config.admin.logo_url,
                authentication_backend=auth,
            )

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
        self.logger.info(f"App started in {main_start_time} s")
        yield
        await cache.close()
        self.logger.error("Application shut down")


depends.set(App)
app = depends.get(App)
