from acb.config import AdapterBase
from acb.config import AppSettings as AppConfigSettings


class AppBaseSettings(AppConfigSettings):
    name: str = "fastblocks"
    style: str = "bulma"
    theme: str = "light"


class AppBase(AdapterBase): ...
