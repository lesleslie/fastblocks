import typing as t
from contextlib import asynccontextmanager
from time import perf_counter

from acb.adapters import get_adapter, import_adapter
from acb.adapters.app import post_startup
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
        """Initialize templates and routes during startup."""
        self.templates = depends.get().app
        self.routes.extend(depends.get("routes").routes)

    @asynccontextmanager
    @depends.inject
    async def lifespan(
        self, app: FastBlocks, sql: Sql = depends(), auth: Auth = depends()
    ) -> t.AsyncIterator[None]:
        try:
            if get_adapter("admin"):
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

            await post_startup()
            main_start_time = perf_counter() - main_start
            self.logger.warning(f"App started in {main_start_time} s")
        except Exception as e:
            self.logger.error(f"Error during startup: {e}")
            raise e
        yield
        self.logger.critical("Application shut down")
        await self.logger.complete()


depends.set(App)
