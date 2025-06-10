from acb import register_pkg
from acb.depends import depends

register_pkg()
app = depends.get()
logger = depends.get()
logger.info(f"Starting application at: {app.__module__}")
