from contextlib import asynccontextmanager
from time import perf_counter

from acb.adapters.cache import Cache
from acb.adapters.storage import Storage
from acb.depends import depends
from acb.config import Config
from acb.adapters.logger import Logger

from fastblocks.applications import FastBlocks
from fastblocks.middleware import middlewares
from fastblocks.routing import router_registry
from ._base import AppBase
from ._base import AppBaseSettings

main_start = perf_counter()


class AppSettings(AppBaseSettings):
    ...


class App(FastBlocks, AppBase):
    @depends.inject
    def __init__(self, config: Config = depends()) -> None:
        super().__init__(
            debug=config.debug.app,
            middleware=middlewares(),
            lifespan=self.lifespan,
        )

    async def init(self) -> None:
        from fastblocks.adapters.templates import Templates

        self.templates = depends.get(Templates).app

        from fastblocks.adapters.admin import Admin

        self.admin = depends.get(Admin)

        for router in router_registry.get():
            super().routes.append(router)

    @depends.inject
    @asynccontextmanager
    async def lifespan(
        self,
        config: Config = depends(),
        logger: Logger = depends(),  # type: ignore
        cache: Cache = depends(),  # type: ignore
        storage: Storage = depends(),  # type: ignore
    ):
        logger.info("Application starting...")

        async def post_startup() -> None:
            if not config.deployed:
                from aioconsole import aprint
                from pyfiglet import Figlet  # type: ignore

                fig = Figlet(font="slant", width=90, justify="center")
                await aprint(f"\n\n{fig.renderText(config.app.name.upper())}\n")
            if not config.debug.production and config.app.deployed:
                logger.info("Entering production mode...")

        await post_startup()
        main_start_time = perf_counter() - main_start
        logger.info(f"App started in {main_start_time} s")
        yield
        await cache.close()
        logger.error("Application shut down")


depends.set(App)
app = depends.get(App)
