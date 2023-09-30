import typing as t
from abc import ABC
from abc import abstractmethod
from contextvars import ContextVar

from acb.adapters.sql import SqlModel
from sqlmodel import Field

from fastblocks import Request
from pydantic import EmailStr
from pydantic import UUID4
from sqlalchemy_utils.types import URLType
from sqlalchemy_utils.types import EmailType
from starlette.authentication import UnauthenticatedUser

current_user: ContextVar[t.Any] = ContextVar(
    "current_user", default=UnauthenticatedUser()
)


class User(SqlModel):
    uid: t.Optional[str] = Field(unique=True)
    name: str
    gmail: EmailStr = Field(unique=True, nullable=False)
    email: t.Optional[EmailType] = Field(unique=True, nullable=False)
    image: t.Optional[URLType]
    is_active: bool = Field(default=True)
    is_superuser: bool = Field(default=False)


class AuthUser(ABC):
    @abstractmethod
    def has_role(self, role: str) -> str:
        raise NotImplementedError

    @abstractmethod
    def set_role(self, role: str) -> str | bool | None:
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
        self, request: t.Optional[Request] = None, config: t.Any = None
    ) -> bool | int | str:
        raise NotImplementedError
