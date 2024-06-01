import typing as t

from acb.adapters import import_adapter
from acb.depends import depends
from sqladmin import Admin as SqlAdmin
from sqladmin.helpers import get_object_identifier
from starlette.applications import Starlette
from starlette_async_jinja import AsyncJinja2Templates
from fastblocks import FastBlocks
from ._base import AdminBase, AdminBaseSettings

Templates = import_adapter()


class AdminSettings(AdminBaseSettings): ...


class Admin(AdminBase, SqlAdmin):  # type: ignore
    def __init__(self, app: Starlette = FastBlocks(), **kwargs: t.Any) -> None:
        super().__init__(app, **kwargs)

    @depends.inject
    async def init(self) -> None:  # type: ignore
        ...

    @depends.inject
    @t.override
    def init_templating_engine(
        self,
        templates: Templates = depends(),  # type: ignore
    ) -> AsyncJinja2Templates:
        admin_templates = templates.admin
        admin_templates_env_globals = dict(
            min=min,
            zip=zip,
            admin=self,
            is_list=lambda x: isinstance(x, list),  # type: ignore
            get_object_identifier=get_object_identifier,
        )
        admin_templates.env.globals.update(admin_templates_env_globals)
        return admin_templates


depends.set(Admin)
