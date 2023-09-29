import logging

from acb.config import register_package
from acb.adapters.logger import register_loggers
from fastblocks.applications import FastBlocks
from fastblocks.applications import Request
from fastblocks.templating import templates
from starlette.responses import HTMLResponse as Response

__all__ = [
    "FastBlocks",
    "templates",
    "Request",
    "Response",
]

register_package()

logging.getLogger("uvicorn").handlers.clear()

register_loggers(["uvicorn.access", "uvicorn.error"])
