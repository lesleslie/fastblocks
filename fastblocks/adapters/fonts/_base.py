from acb.config import Settings
from acb.adapters import AdapterBase


class FontsBaseSettings(Settings):
    primary: str
    secondary: str
    icons: str = "fontawesome"
    fontawesome_pro: bool = True
    fontawesome_kit: str = ""


class FontsBase(AdapterBase): ...
