from acb.config import AdapterBase, Settings


class AdminBaseSettings(Settings):  # type: ignore[misc]
    style: str = "bootstrap"
    title: str = "FastBlocks Dashboard"


class AdminBase(AdapterBase): ...  # type: ignore[misc]
