from acb.adapters import AdapterBase
from acb.config import Settings


class AdminBaseSettings(Settings):
    style: str = "bootstrap"
    title: str = "FastBlocks Dashboard"


class AdminBase(AdapterBase): ...
