import base64
import binascii
import typing as t

from acb.depends import depends
from asgi_htmx import HtmxRequest
from pydantic import UUID4, EmailStr, SecretStr
from starlette.authentication import AuthCredentials, AuthenticationError, SimpleUser
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware

from ._base import AuthBase, AuthBaseSettings


class AuthSettings(AuthBaseSettings): ...


class AuthBasicUser:
    def has_role(self, role: str) -> str: ...  # noqa: F841
    def set_role(self, role: str) -> str | bool | None: ...  # noqa: F841

    @property
    def identity(self) -> UUID4 | str | int: ...

    @property
    def display_name(self) -> str: ...

    @property
    def email(self) -> EmailStr | None: ...

    def is_authenticated(
        self, request: t.Optional[HtmxRequest] = None, config: t.Any = None
    ) -> bool | int | str: ...


class Auth(AuthBase):
    secret_key: SecretStr

    @property
    def current_user(self) -> t.Any:
        return self._current_user.get()

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
            raise AuthenticationError("Invalid basic auth credentials")

        username, _, password = decoded.partition(":")  # type: ignore
        # TODO: You'd want to verify the username and password here.
        # password variable is intentionally captured for future implementation

        # Store the authentication credentials in the request state for later use
        request.state.auth_credentials = (
            AuthCredentials(["authenticated"]),
            SimpleUser(username),
        )
        return True

    def __init__(
        self,
        secret_key: SecretStr = SecretStr("secret"),
        user_model: t.Optional[t.Any] = None,
    ) -> None:
        super().__init__(secret_key, user_model)
        self.secret_key = secret_key or self.config.app.secret_key
        # Get token_id from settings or use a default
        token_id = getattr(self.config.auth, "token_id", "fastblocks")
        self.token_id = token_id
        self.middlewares = [
            Middleware(
                SessionMiddleware,  # type: ignore
                secret_key=self.secret_key.get_secret_value(),
                session_cookie=f"{self.token_id}_admin",
                https_only=True if self.config.deployed else False,
            )
        ]
        self.name = "basic"
        self.user_model = user_model

    async def init(self) -> None: ...

    async def login(self, request: HtmxRequest) -> bool: ...

    async def logout(self, request: HtmxRequest) -> bool: ...


depends.set(Auth)
