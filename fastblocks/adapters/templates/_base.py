import typing as t
from abc import ABC
from abc import abstractmethod

from acb.adapters.logger import Logger
from acb.adapters.storage import Storage
from acb.config import Config
from acb.config import Settings
from acb.depends import depends


class TemplatesBaseSettings(Settings):
    ...


class TemplatesBase(ABC):
    logger: Logger = depends()  # type: ignore
    config: Config = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore
    app: t.Optional[t.Any] = None
    admin: t.Optional[t.Any] = None

    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError
