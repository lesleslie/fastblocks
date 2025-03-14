import typing as t

from acb.depends import depends
from asgi_htmx import HtmxRequest
from pydantic import SecretStr
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from ._base import AuthBase, AuthBaseSettings


class AuthSettings(AuthBaseSettings): ...


class Auth(AuthBase):
    secret_key: SecretStr

    @property
    def current_user(self) -> t.Any:
        return self._current_user.get()

    @staticmethod
    async def authenticate(request: HtmxRequest) -> bool: ...

    def __init__(
        self,
        secret_key: SecretStr = SecretStr("secret"),
        user_model: t.Optional[t.Any] = None,
    ) -> None:
        super().__init__(secret_key, user_model)
        self.secret_key = secret_key or self.config.app.secret_key
        self.middlewares = [
            Middleware(
                SessionMiddleware,  # type: ignore
                secret_key=self.secret_key.get_secret_value(),
                session_cookie=f"{self.get_token()}_admin",
                https_only=True if self.config.deployed else False,
            )
        ]
        self.name = "basic"
        self.user_model = user_model

    async def init(self) -> None: ...

    async def login(self, request: HtmxRequest) -> bool: ...

    async def logout(self, request: HtmxRequest) -> bool: ...


depends.set(Auth)
