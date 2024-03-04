from time import perf_counter

from acb.adapters import import_adapter
from acb.config import Config
from acb.depends import depends

from asgi_htmx import HtmxMiddleware
from brotli_asgi import BrotliMiddleware
from secure import Secure
from starlette.applications import Starlette
from starlette.datastructures import MutableHeaders
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.types import Message
from starlette.types import Receive
from starlette.types import Scope
from starlette.types import Send
from starlette_csrf.middleware import CSRFMiddleware

Logger = import_adapter()

secure_headers = Secure()


class SecureHeadersMiddleware:
    def __init__(self, app: Starlette) -> None:
        self.app = app

    @depends.inject
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        logger: Logger = depends(),  # type: ignore
    ) -> None:
        if scope["type"] != "http":
            return await self.app(scope, receive, send)

        async def send_with_secure_headers(message: Message) -> None:
            if message["type"] == "http.response.start":
                headers = MutableHeaders(scope=message)
                for k, v in secure_headers.headers().items():
                    headers.append(k, v)
            await send(message)

        await self.app(scope, receive, send_with_secure_headers)


class ProcessTimeHeaderMiddleware:
    def __init__(self, app: Starlette) -> None:
        self.app = app

    @depends.inject
    async def __call__(
        self,
        scope: Scope,
        receive: Receive,
        send: Send,
        logger: Logger = depends(),  # type: ignore
    ) -> None:
        start_time = perf_counter()
        try:
            await self.app(scope, receive, send)
        except Exception as exc:
            logger.exception(exc)
            raise
        finally:
            process_time = perf_counter() - start_time
            logger.debug(f"Request processed in {process_time} s")


@depends.inject
def middlewares(config: Config = depends()) -> list[Middleware]:  # type: ignore
    middleware = [
        Middleware(ProcessTimeHeaderMiddleware),  # type: ignore
        Middleware(
            CSRFMiddleware,  # type: ignore
            secret=config.app.secret_key.get_secret_value(),
            cookie_name=f"{config.auth.token_id or config.app.name}_csrf",
            cookie_secure=config.deployed,
        ),
        Middleware(
            SessionMiddleware,  # type: ignore
            secret_key=config.app.secret_key.get_secret_value(),
            session_cookie=f"{config.auth.token_id or config.app.name}_app",
            https_only=config.deployed,
        ),
        Middleware(HtmxMiddleware),  # type: ignore
        Middleware(BrotliMiddleware, quality=3),  # type: ignore
    ]
    if config.deployed or config.debug.production:
        middleware.append(Middleware(SecureHeadersMiddleware))  # type: ignore
    return middleware
