import typing as t

from acb.adapters import import_adapter
from acb.depends import depends
from sqladmin import Admin as SqlAdmin
from starlette.applications import Starlette
from fastblocks import FastBlocks

from ._base import AdminBase, AdminBaseSettings

Auth, Storage, Models, Sql, Templates = import_adapter()  # type: ignore


class AdminSettings(AdminBaseSettings): ...


class Admin(AdminBase, SqlAdmin):  # type: ignore
    def __init__(
        self,
        app: Starlette = FastBlocks(),
        templates: Templates = depends(),
        **kwargs: t.Any,
    ) -> None:
        super().__init__(app, **kwargs)  # type: ignore
        self.templates = templates.admin

    @depends.inject
    async def init(self, models: Models = depends(), sql: Sql = depends()) -> None: ...  # noqa


depends.set(Admin)
