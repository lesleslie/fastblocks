import typing as t
from abc import ABC
from abc import abstractmethod

from acb.adapters import import_adapter
from acb.config import Config
from acb.config import Settings
from acb.depends import depends

Logger = import_adapter()


class TemplatesBaseSettings(Settings): ...


class TemplatesBase(ABC):
    logger: Logger = depends()  # type: ignore
    config: Config = depends()  # type: ignore
    app: t.Optional[t.Any] = None
    admin: t.Optional[t.Any] = None

    @abstractmethod
    async def init(self) -> None:
        raise NotImplementedError
