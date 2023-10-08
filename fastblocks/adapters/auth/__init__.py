from acb.config import load_adapter
from ._model import UserModel
from ._base import current_user


__all__: list[str] = [
    "Auth",
    "AuthSettings",
    "UserModel",
    "current_user",
]


Auth, AuthSettings = load_adapter()
