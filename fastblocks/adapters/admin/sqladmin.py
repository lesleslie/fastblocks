"""SQLAdmin Adapter for FastBlocks.

Provides administrative interface using SQLAdmin for database model management.
Includes automatic model discovery and registration with template integration.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import typing as t
from contextlib import suppress
from uuid import UUID

# Oneiric imports
from oneiric.core.resolution import Resolver
from starlette.applications import Starlette
from fastblocks.applications import FastBlocks

from ..oneiric_helper import register_candidate
from ._base import AdminBase, AdminBaseSettings

# Custom Oneiric-compatible adapter system
depends = Resolver()
_using_oneiric = True

Auth = None
Storage = None
Models = None
Sql = None
Templates = None


class AdminSettings(AdminBaseSettings): ...


class Admin(AdminBase):
    def __init__(
        self,
        templates: t.Any | None = None,
        app: Starlette | None = None,
        **kwargs: t.Any,
    ) -> None:
        super().__init__()
        from sqladmin import Admin as SqlAdminBase

        if app is None:
            app = FastBlocks()

        self._sqladmin = SqlAdminBase(app=app, **kwargs)
        self.templates = templates.admin if templates else None

    def __getattr__(self, name: str) -> t.Any:
        return getattr(self._sqladmin, name)

    async def init(self) -> None:
        with suppress(Exception):
            # For Oneiric, try to get models using resolve
            try:
                models = await depends.resolve("fastblocks", "models")
                if models and hasattr(models, "get_admin_models"):
                    admin_models = models.get_admin_models()
                    for model in admin_models:
                        self._sqladmin.add_view(model)
            except Exception:
                pass  # Gracefully handle any dependency resolution errors


MODULE_ID = UUID("01937d86-7f5d-7e6f-b120-4567890123de")
MODULE_STATUS = "STABLE"  # Oneiric-compatible status

# Register with Oneiric resolver
register_candidate(
    depends,
    domain="fastblocks",
    key="admin",
    factory=Admin,
    metadata={
        "class": "Admin",
        "module": "fastblocks.adapters.admin.sqladmin",
    },
)
