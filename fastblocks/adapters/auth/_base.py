import typing as t
from abc import ABC
from abc import abstractmethod

from acb.adapters.sql import SqlModel
from acb.config import Settings

from fastblocks import Request
from pydantic import SecretStr


class AuthBaseSettings(Settings):
    token_id: t.Optional[str] = None
    session_cookie: t.Optional[str] = None


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
