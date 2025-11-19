from acb.config import AdapterBase, Settings


class AdminBaseSettings(Settings):
    style: str = "bootstrap"
    title: str = "FastBlocks Dashboard"


class AdminBase(AdapterBase): ...
