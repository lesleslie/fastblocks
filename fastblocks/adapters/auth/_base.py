import typing as t
from contextvars import ContextVar

from acb.config import AdapterBase, Settings
from acb.depends import depends
from asgi_htmx import HtmxRequest
from pydantic import UUID4, EmailStr, SecretStr
from starlette.authentication import UnauthenticatedUser


class AuthBaseSettings(Settings):
    token_id: str | None = None

    @depends.inject
    def __init__(self, config: t.Any = depends(), **data: t.Any) -> None:
        super().__init__(**data)
        self.token_id = self.token_id or getattr(config.app, "token_id", "_fb_")


class CurrentUser(t.Protocol):
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


class AuthProtocol(t.Protocol):
    _current_user: ContextVar[t.Any]

    @property
    def current_user(self) -> t.Any: ...

    async def authenticate(self, request: HtmxRequest) -> bool: ...

    async def login(self, request: HtmxRequest) -> bool: ...

    async def logout(self, request: HtmxRequest) -> bool: ...


class AuthBase(AdapterBase):
    _current_user: ContextVar[t.Any] = ContextVar(
        "current_user",
        default=UnauthenticatedUser(),
    )

    @property
    def current_user(self) -> t.Any:
        return self._current_user.get()

    @property
    def token_id(self) -> str:
        return self.config.auth.token_id

    @staticmethod
    async def authenticate(request: HtmxRequest) -> bool: ...

    def __init__(
        self, secret_key: SecretStr, user_model: t.Any, **kwargs: t.Any
    ) -> None:
        super().__init__(**kwargs)

    async def init(self) -> None: ...

    async def login(self, request: HtmxRequest) -> bool: ...

    async def logout(self, request: HtmxRequest) -> bool: ...
