import typing as t
from contextvars import ContextVar

# Oneiric imports
from oneiric.core.config import OneiricSettings
from pydantic import UUID4, EmailStr, SecretStr
from starlette.authentication import UnauthenticatedUser
from fastblocks.htmx import HtmxRequest


class AuthBaseSettings(OneiricSettings):
    """Auth base settings using OneiricSettings."""

    token_id: str | None = None

    def __init__(self, **data: t.Any) -> None:
        super().__init__(**data)
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual config resolution
        self.token_id = self.token_id or "_fb_"


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


class AuthBase:
    """Auth base adapter using Oneiric."""

    _current_user: ContextVar[t.Any] = ContextVar(
        "current_user",
        default=UnauthenticatedUser(),
    )

    @property
    def current_user(self) -> t.Any:
        return self._current_user.get()

    @property
    def token_id(self) -> str:
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual config resolution
        return "_fb_"

    @staticmethod
    async def authenticate(request: HtmxRequest) -> bool:
        raise NotImplementedError

    def __init__(
        self, secret_key: SecretStr, user_model: t.Any, **kwargs: t.Any
    ) -> None:
        self.secret_key = secret_key
        self.user_model = user_model

    async def init(self) -> None:
        raise NotImplementedError

    async def login(self, request: HtmxRequest) -> bool:
        raise NotImplementedError

    async def logout(self, request: HtmxRequest) -> bool:
        raise NotImplementedError
