import typing as t
from abc import ABC, abstractmethod
from contextvars import ContextVar

from acb.config import AdapterBase, Settings
from asgi_htmx import HtmxRequest
from pydantic import UUID4, EmailStr, SecretStr
from starlette.authentication import UnauthenticatedUser


class AuthBaseSettings(Settings):
    token_id: t.Optional[str] = None
    session_cookie: t.Optional[str] = None


class AuthBase(AdapterBase, ABC):
    _current_user: ContextVar[t.Any] = ContextVar(
        "current_user", default=UnauthenticatedUser()
    )

    @property
    def current_user(self) -> t.Any:
        return self._current_user.get()

    @staticmethod
    @abstractmethod
    async def authenticate(request: HtmxRequest) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __init__(self, secret_key: SecretStr, user_model: t.Any) -> None:  # noqa: F841
        raise NotImplementedError

    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def login(self, request: HtmxRequest) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def logout(self, request: HtmxRequest) -> bool:
        raise NotImplementedError


class AuthBaseUser(ABC):
    @abstractmethod
    def has_role(self, role: str) -> str:  # noqa: F841
        raise NotImplementedError

    @abstractmethod
    def set_role(self, role: str) -> str | bool | None:  # noqa: F841
        raise NotImplementedError

    @property
    @abstractmethod
    def identity(self) -> UUID4 | str | int:
        raise NotImplementedError

    @property
    @abstractmethod
    def display_name(self) -> str:
        raise NotImplementedError

    @property
    @abstractmethod
    def email(self) -> EmailStr:
        raise NotImplementedError

    @abstractmethod
    def is_authenticated(
        self, request: t.Optional[HtmxRequest] = None, config: t.Any = None
    ) -> bool | int | str:
        raise NotImplementedError
