from pathlib import Path

from acb import register_pkg
from acb.depends import depends

register_pkg()

app = depends.get()
logger = depends.get()

print(Path.cwd())

logger.info(f"Starting application at: {app.__module__}")
