import typing as t
from contextlib import suppress

from acb.depends import depends
from starlette.applications import Starlette
from fastblocks.applications import FastBlocks

from ._base import AdminBase, AdminBaseSettings

Auth = None
Storage = None
Models = None
Sql = None
Templates = None


class AdminSettings(AdminBaseSettings): ...


class Admin(AdminBase):
    def __init__(
        self,
        app: Starlette = FastBlocks(),
        templates: t.Any = depends(),
        **kwargs: t.Any,
    ) -> None:
        super().__init__()
        from sqladmin import Admin as SqlAdminBase

        self._sqladmin = SqlAdminBase(app=app, **kwargs)
        self.templates = templates.admin

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self._sqladmin, name)

    async def init(self) -> None:
        with suppress(Exception):
            models = depends.get("models")
            if hasattr(models, "get_admin_models"):
                admin_models = models.get_admin_models()
                for model in admin_models:
                    self._sqladmin.add_view(model)


with suppress(Exception):
    depends.set(Admin)
