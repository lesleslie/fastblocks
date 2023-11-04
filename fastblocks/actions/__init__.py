from acb.actions import compress
from acb.actions import encode
from acb.actions import hash
from acb.actions import register_actions
from fastblocks.actions import minify

__all__: list[str] = ["encode", "hash", "compress", "minify"]

register_actions()
