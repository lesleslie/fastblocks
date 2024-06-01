from acb.adapters import AdapterBase
from acb.config import AppSettings as AppConfigSettings


class AppBaseSettings(AppConfigSettings):
    project: str = "fastblocks"
    name: str = "fastblocks"
    title: str = "FastBlocks"
    style: str = "bulma"
    theme: str = "light"


class AppBase(AdapterBase): ...
