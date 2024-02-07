from acb.config import Config
from acb.depends import depends

from asgi_htmx import HtmxMiddleware
from brotli_asgi import BrotliMiddleware
from starlette.middleware import Middleware
from starlette_csrf.middleware import CSRFMiddleware


@depends.inject
def middlewares(config: Config = depends()) -> list[Middleware]:  # type: ignore
    middleware = [
        Middleware(
            CSRFMiddleware,  # type: ignore
            secret=config.app.secret_key.get_secret_value(),
        ),
        Middleware(HtmxMiddleware),  # type: ignore
        Middleware(BrotliMiddleware, quality=3),  # type: ignore
    ]
    return middleware
