import typing as t
from abc import ABC
from abc import abstractmethod

from acb.config import AppSettings as AppConfigSettings


class AppBaseSettings(AppConfigSettings):
    style: str = "bulma"
    theme: str = "light"


class AppBase(ABC):
    @abstractmethod
    def __init__(self, **kwargs: t.Any) -> None:
        super().__init__(**kwargs)
        raise NotImplementedError

    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError

    @abstractmethod
    async def lifespan(self) -> None:
        raise NotImplementedError
