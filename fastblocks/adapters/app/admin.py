from contextlib import asynccontextmanager
from time import time

from acb import adapter_registry
from acb.adapters.cache import Cache
from acb.adapters.logger import Logger
from acb.adapters.sql import SqlModels
from acb.adapters.sql import Sql
from acb.config import Config
from acb.depends import depends
from fastblocks.adapters.admin import Admin
from fastblocks.adapters.auth import Auth
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
    media_types: list[str] = ["image", "video", "audio"]
    video_exts: list[str] = [".webm", ".m4v", ".mp4"]
    image_exts: list[str] = [".jpeg", ".jpg", ".png", ".webp"]
    audio_exts: list[str] = [".m4a", ".mp4"]
    allowed_exts: list[str] = [
        ".html",
        ".scss",
        ".json",
        ".js",
        ".yml",
        ".py",
        ".ini",
        ".gz",
        ".txt",
    ]
    notification_icons: dict[str, str] = dict(
        info="info-circle",
        success="check-circle",
        danger="exclamation-circle",
        warning="exclamation-triangle",
    )
    wtf_csrf_time_limit: int = 172_800


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
        config: Config = depends(),  # type: ignore
        logger: Logger = depends(),  # type: ignore
        models: SqlModels = depends(),  # type: ignore
        cache: Cache = depends(),  # type: ignore
        sql: Sql = depends(),  # type: ignore
        auth: Auth = depends(),  # type: ignore
        admin: Admin = depends(),  # type: ignore
    ):
        logger.info("Application starting...")
        if next(a for a in adapter_registry.get() if a.name == "admin" and a.installed):
            # try:
            #     logger.info("Creating admin superuser...")
            #     await models.create_user(
            #         gmail=config.admin.gmail,
            #         email=config.admin.email,
            #         role="admin",
            #     )
            # except IntegrityError:
            #     logger.debug("Admin superuser exists")
            admin.__init__(
                app=self,
                engine=sql.engine,
                title=config.admin.title,
                debug=config.debug.admin,
                base_url=config.admin.url,
                logo_url=config.admin.logo_url,
                authentication_backend=auth,
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
        main_start_time = time() - main_start
        logger.info(f"App started in {main_start_time} s")
        yield
        await cache.close()
        logger.error("Application shut down")


depends.set(App)

app = depends.get(App)
