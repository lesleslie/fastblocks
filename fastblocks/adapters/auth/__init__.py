import typing as t
from abc import ABC
from abc import abstractmethod
from contextvars import ContextVar

from acb.config import Settings
from fastblocks import Request
from pydantic import EmailStr
from pydantic import UUID4
from starlette.authentication import UnauthenticatedUser
from acb.adapters.sql import SqlModel
from pydantic import SecretStr

current_user: ContextVar[t.Any] = ContextVar(
    "current_user", default=UnauthenticatedUser()
)


class AuthBaseSettings(Settings):
    token_id: t.Optional[str] = None
    session_cookie: t.Optional[str] = None


class User(ABC):
    @abstractmethod
    def has_role(self, role: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_role(self, role: str) -> str | bool:
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

    @property
    @abstractmethod
    def is_authenticated(self, request: t.Optional[Request] = None) -> bool:
        raise NotImplementedError


class AuthBase(ABC):
    @staticmethod
    @abstractmethod
    async def authenticate(request: Request) -> bool:
        raise NotImplementedError

    @abstractmethod
    def __init__(self, secret_key: SecretStr, user_model: SqlModel) -> None:
        raise NotImplementedError

    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def login(self, request: Request) -> bool:
        raise NotImplementedError

    @abstractmethod
    async def logout(self, request: Request) -> bool:
        raise NotImplementedError
