from ...dependencies import get_acb_subset

AdapterBase, Settings = get_acb_subset("AdapterBase", "Settings")


class AdminBaseSettings(Settings):
    style: str = "bootstrap"
    title: str = "FastBlocks Dashboard"


class AdminBase(AdapterBase): ...
