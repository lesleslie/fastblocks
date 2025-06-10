import typing as t

from acb.adapters import import_adapter
from acb.depends import depends
from starlette.applications import Starlette
from fastblocks.applications import FastBlocks

from ._base import AdminBase, AdminBaseSettings

Auth, Storage, Models, Sql, Templates = import_adapter()


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

    @depends.inject
    async def init(self, models: t.Any = depends()) -> None:
        if hasattr(models, "get_admin_models"):
            admin_models = models.get_admin_models()
            for model in admin_models:
                self._sqladmin.add_view(model)


depends.set(Admin)
