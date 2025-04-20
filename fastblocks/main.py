from acb import register_pkg
from acb.depends import depends
from fastblocks.applications import FastBlocks  # noqa  # type: ignore

register_pkg()

app = depends.get()
logger = depends.get()

logger.info(f"Starting application at: {app.__module__}")
