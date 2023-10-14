from abc import ABC, abstractmethod
from acb.config import AppSettings as AppConfigSettings
import typing as t


class AppBaseSettings(AppConfigSettings):
    requires: t.Optional[list[str]] = ["cache", "sql", "storage", "templates"]


class AppBase(ABC):
    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def lifespan(self) -> None:
        raise NotImplementedError
