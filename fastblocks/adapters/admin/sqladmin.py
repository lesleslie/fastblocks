"""SQLAdmin Adapter for FastBlocks.

Provides administrative interface using SQLAdmin for database model management.
Includes automatic model discovery and registration with template integration.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import typing as t
from contextlib import suppress
from uuid import UUID

from acb.adapters import AdapterStatus
from acb.depends import Inject, depends
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
    @depends.inject
    def __init__(
        self,
        templates: Inject[t.Any],
        app: Starlette | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__()
        from sqladmin import Admin as SqlAdminBase

        if app is None:
            app = FastBlocks()

        self._sqladmin = SqlAdminBase(app=app, **kwargs)
        self.templates = templates.admin

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self._sqladmin, name)

    async def init(self) -> None:
        with suppress(Exception):
            models = await depends.get("models")
            if hasattr(models, "get_admin_models"):
                admin_models = models.get_admin_models()
                for model in admin_models:
                    self._sqladmin.add_view(model)


MODULE_ID = UUID("01937d86-7f5d-7e6f-b120-4567890123de")
MODULE_STATUS = AdapterStatus.STABLE

with suppress(Exception):
    depends.set(Admin, "sqladmin")
