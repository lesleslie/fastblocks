from acb.adapters import load_adapter
from ._model import UserModel
from ._base import current_user


__all__: list[str] = [
    "Auth",
    "UserModel",
    "current_user",
]


Auth = load_adapter()
