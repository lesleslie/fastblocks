import typing as t
from abc import ABC

from acb.adapters import AdapterBase
from acb.adapters import import_adapter
from acb.config import Settings

Logger = import_adapter()


class TemplatesBaseSettings(Settings): ...


class TemplatesBase(AdapterBase, ABC):
    app: t.Optional[t.Any] = None
    admin: t.Optional[t.Any] = None
