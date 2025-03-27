import typing as t
from base64 import b64encode
from contextvars import ContextVar

from acb.config import AdapterBase, Config, Settings
from acb.depends import depends
from asgi_htmx import HtmxRequest
from pydantic import UUID4, EmailStr, SecretStr
from starlette.authentication import UnauthenticatedUser


class AuthBaseSettings(Settings):
    token_id: t.Optional[str] = "_fb_"

    @depends.inject
    def __init__(self, config: Config = depends(), **data: t.Any) -> None:
        super().__init__(**data)
        self.token_id = "".join(  # type: ignore
            [self.token_id, b64encode(config.app.name.encode()).decode().rstrip("=")]  # type: ignore
        )


class CurrentUser(t.Protocol):
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


class AuthProtocol(t.Protocol):
    _current_user: ContextVar[t.Any]

    @property
    def current_user(self) -> t.Any: ...
    async def authenticate(self, request: HtmxRequest) -> bool: ...
    async def login(self, request: HtmxRequest) -> bool: ...
    async def logout(self, request: HtmxRequest) -> bool: ...


class AuthBase(AdapterBase):
    _current_user: ContextVar[t.Any] = ContextVar(
        "current_user", default=UnauthenticatedUser()
    )

    @property
    def current_user(self) -> t.Any:
        return self._current_user.get()

    @property
    def token_id(self) -> str:
        return self.config.auth.token_id

    @staticmethod
    async def authenticate(request: HtmxRequest) -> bool: ...

    def __init__(self, secret_key: SecretStr, user_model: t.Any) -> None: ...

    async def init(self) -> None: ...

    async def login(self, request: HtmxRequest) -> bool: ...

    async def logout(self, request: HtmxRequest) -> bool: ...
