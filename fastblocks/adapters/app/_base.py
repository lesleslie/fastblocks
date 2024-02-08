from acb.config import AppSettings as AppConfigSettings
from acb.adapters import AdapterBase


class AppBaseSettings(AppConfigSettings):
    style: str = "bulma"
    theme: str = "light"


class AppBase(AdapterBase): ...
