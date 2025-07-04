from ...dependencies import get_acb_subset

AdapterBase, Settings = get_acb_subset("AdapterBase", "Settings")


class RoutesBaseSettings(Settings): ...


class RoutesBase(AdapterBase): ...
