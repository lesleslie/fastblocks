from contextlib import asynccontextmanager
from time import time

from acb.adapters.cache import Cache
from acb.adapters.logger import Logger
from acb.adapters.storage import Storage
from acb.config import Config
from acb.depends import depends
from fastblocks.adapters.templates import Templates
from fastblocks.applications import FastBlocks
from fastblocks.routing import router_registry
from middleware import middlewares
from ._base import AppBase
from ._base import AppBaseSettings

main_start = time()


class AppSettings(AppBaseSettings):
    style: str = "bulma"
    theme: str = "light"


class App(FastBlocks, AppBase):
    config: Config = depends()  # type: ignore
    templates: Templates = depends()  # type: ignore

    def __init__(self) -> None:
        super().__init__(
            debug=self.config.debug.app,
            middleware=middlewares(),
            lifespan=self.lifespan,
        )
        self.templates = self.templates.app

    async def init(self) -> None:
        for router in router_registry.get():
            super().routes.append(router)

    @depends.inject
    @asynccontextmanager
    async def lifespan(
        self,
        logger: Logger = depends(),  # type: ignore
        cache: Cache = depends(),  # type: ignore
        storage: Storage = depends(),  # type: ignore
    ):
        logger.info("Application starting...")

        async def post_startup() -> None:
            if not self.config.deployed:
                from aioconsole import aprint
                from pyfiglet import Figlet  # type: ignore

                fig = Figlet(font="slant", width=90, justify="center")
                await aprint(f"\n\n{fig.renderText(self.config.app.name.upper())}\n")
            if not self.config.debug.production and self.config.app.deployed:
                logger.info("Entering production mode...")

        await post_startup()
        main_start_time = time() - main_start
        logger.info(f"App started in {main_start_time} s")
        yield
        await cache.close()
        logger.error("Application shut down")


depends.set(App)

app = depends.get(App)
