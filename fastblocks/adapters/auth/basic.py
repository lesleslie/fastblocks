import base64
import binascii
import typing as t
from contextlib import suppress

from acb.depends import depends
from asgi_htmx import HtmxRequest
from pydantic import UUID4, EmailStr, SecretStr
from starlette.authentication import AuthCredentials, AuthenticationError, SimpleUser
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from ._base import AuthBase, AuthBaseSettings


class AuthSettings(AuthBaseSettings): ...


class CurrentUser:
    def has_role(self, _: str) -> str: ...

    def set_role(self, _: str) -> str | bool | None: ...

    @property
    def identity(self) -> UUID4 | str | int: ...

    @property
    def display_name(self) -> str: ...

    @property
    def email(self) -> EmailStr | None: ...

    def is_authenticated(
        self,
        request: HtmxRequest | None = None,
        config: t.Any = None,
    ) -> bool | int | str: ...


class Auth(AuthBase):
    secret_key: SecretStr

    @staticmethod
    async def authenticate(request: HtmxRequest) -> bool:
        if "Authorization" not in request.headers:
            return False
        auth = request.headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != "basic":
                return False
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            msg = "Invalid basic auth credentials"
            raise AuthenticationError(msg)
        username, _, _ = decoded.partition(":")
        request.state.auth_credentials = (
            AuthCredentials(["authenticated"]),
            SimpleUser(username),
        )
        return True

    def __init__(
        self,
        secret_key: SecretStr = SecretStr("secret"),
        user_model: t.Any | None = None,
    ) -> None:
        super().__init__(secret_key, user_model)
        self.secret_key = secret_key or self.config.app.secret_key
        self.name = "basic"
        self.user_model = user_model

    async def init(self) -> None:
        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=self.secret_key.get_secret_value(),
                session_cookie=f"{self.token_id}_admin",
                https_only=bool(self.config.deployed),
            ),
        ]

    async def login(self, request: HtmxRequest) -> bool: ...

    async def logout(self, request: HtmxRequest) -> bool: ...


with suppress(Exception):
    depends.set(Auth)
