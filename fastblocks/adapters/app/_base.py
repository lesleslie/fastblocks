from acb.config import AppSettings as AppConfigSettings
from acb.adapters import AdapterBase


class AppBaseSettings(AppConfigSettings):
    project: str = "fastblocks"
    name: str = "fastblocks"
    title: str = "FastBlocks"
    style: str = "bulma"
    theme: str = "light"


class AppBase(AdapterBase): ...
