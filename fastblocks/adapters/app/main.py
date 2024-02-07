from contextlib import asynccontextmanager
from importlib import import_module
from time import perf_counter

from acb.adapters import get_adapter
from acb.adapters.cache import Cache
from acb.adapters.logger import Logger
from acb.adapters.storage import Storage
from acb.config import Config
from acb.debug import debug
from acb.depends import depends

from fastblocks.applications import FastBlocks
from fastblocks.routing import route_registry
from ._base import AppBase
from ._base import AppBaseSettings

main_start = perf_counter()


class AppSettings(AppBaseSettings): ...


class App(FastBlocks, AppBase):
    @depends.inject
    def __init__(self) -> None:  # type: ignore
        super().__init__(lifespan=self.lifespan)
        self.templates = None
        self.auth = None
        self.models = depends.get(
            import_module(".".join(get_adapter("models").path.parts)).Models
        )
        # for model in dir(self.models):
        #     debug(model)

    async def init(self) -> None:
        auth_cls = import_module(".".join(get_adapter("auth").path.parts)).Auth
        self.auth = depends.get(auth_cls)

        templates_cls = import_module(
            ".".join(get_adapter("templates").path.parts)
        ).Templates
        self.templates = depends.get(templates_cls).app
        routes_cls = import_module(".".join(get_adapter("routes").path.parts)).Routes
        routes = depends.get(routes_cls).routes
        route_registry.get().append(routes)
        for route in routes:
            debug(route)

    @depends.inject
    @asynccontextmanager
    async def lifespan(
        self,
        config: Config = depends(),
        logger: Logger = depends(),  # type: ignore
        cache: Cache = depends(),  # type: ignore
        storage: Storage = depends(),  # type: ignore
    ):
        from acb.adapters.sql import Sql

        sql = depends.get(Sql)

        if get_adapter("admin").enabled:
            admin_cls = import_module(".".join(get_adapter("admin").path.parts)).Admin

            admin = depends.get(admin_cls)

            admin.__init__(
                app,
                engine=sql.engine,
                title=config.admin.title,
                debug=config.debug.admin,
                base_url=config.admin.url,
                logo_url=config.admin.logo_url,
                authentication_backend=self.auth,
            )

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
