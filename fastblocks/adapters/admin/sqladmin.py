import typing as t
from typing import override

from acb.adapters.logger import Logger
from acb.adapters.models import Models
from acb.adapters.storage import Storage
from acb.config import Config
from acb.config import Settings
from acb.depends import depends
from sqladmin.helpers import get_object_identifier

from fastblocks import AsyncJinja2Templates
from fastblocks import RedirectResponse
from fastblocks import Response
from sqladmin import Admin as SqlAdmin
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from ..templates import Templates


# from wtforms.fields import TextAreaField
# from wtforms.widgets import TextArea
# from wtforms.fields.datetime import DateTimeField


class AdminSettings(Settings):
    requires: list[str] = ["app", "storage", "sql", "auth"]
    title: str = "Fastblocks Dashboard"
    roles: t.Optional[list[str]] = ["admin", "owner", "contributor", "viewer"]


class Admin(SqlAdmin):
    config: Config = depends()  # type: ignore
    logger: Logger = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore
    templates: Templates = depends()  # type: ignore

    def __init__(self, app: Starlette = Starlette(), **kwargs: t.Any) -> None:
        self.templates = self.templates.admin
        super().__init__(app, **kwargs)

    @depends.inject
    async def init(self, models: Models = depends()) -> None:  # type: ignore
        ...

    @depends.inject
    def init_templating_engine(
        self, templates: Templates = depends()  # type: ignore
    ) -> AsyncJinja2Templates:
        tmpls = templates.admin
        tmpls.env.globals["min"] = min
        tmpls.env.globals["zip"] = zip
        tmpls.env.globals["admin"] = self
        tmpls.env.globals["is_list"] = lambda x: isinstance(x, list)  # type: ignore
        tmpls.env.globals["get_object_identifier"] = get_object_identifier
        return tmpls

    @override
    async def login(self, request: Request) -> (RedirectResponse | Response):
        if self.authentication_backend:
            context = {"request": request, "error": ""}
            ok = await self.authentication_backend.login(request)
            if ok:
                return RedirectResponse(request.url_for("admin:index"), status_code=302)
            context["error"] = "Invalid credentials."
            return await self.templates.render_template(
                "login.html", context, status_code=200
            )
        return RedirectResponse(request.url_for("admin:index"), status_code=400)

    async def http_exception(self, request: Request, exc: Exception) -> Response | None:
        if isinstance(exc, HTTPException):
            context = {
                "request": request,
                "status_code": exc.status_code,
                "message": exc.detail,
            }
            return await self.templates.render_template(
                "error.html", context, status_code=exc.status_code
            )
