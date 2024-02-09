import typing as t
from typing import override

from acb.adapters import import_adapter
from acb.config import Config
from acb.depends import depends
from starlette_async_jinja import AsyncJinja2Templates

from sqladmin import Admin as SqlAdmin
from sqladmin.helpers import get_object_identifier
from starlette.applications import Starlette
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import RedirectResponse
from starlette.responses import Response
from ._base import AdminBase
from ._base import AdminBaseSettings

# from wtforms.fields import TextAreaField
# from wtforms.widgets import TextArea
# from wtforms.fields.datetime import DateTimeField

Logger = import_adapter()
Storage = import_adapter()
Templates = import_adapter()


class AdminSettings(AdminBaseSettings):
    title: str = "Fastblocks Dashboard"
    roles: t.Optional[list[str]] = ["admin", "owner", "contributor", "viewer"]


class Admin(SqlAdmin, AdminBase):
    config: Config = depends()  # type: ignore
    logger: Logger = depends()  # type: ignore
    storage: Storage = depends()  # type: ignore
    templates: Templates = depends()  # type: ignore

    def __init__(self, app: Starlette = Starlette(), **kwargs: t.Any) -> None:
        self.templates = self.templates.admin
        super().__init__(app, **kwargs)

    @depends.inject
    async def init(self) -> None:  # type: ignore
        ...

    @override
    def init_templating_engine(self) -> AsyncJinja2Templates:  # type: ignore
        self.templates.env.globals["min"] = min
        self.templates.env.globals["zip"] = zip
        self.templates.env.globals["admin"] = self
        self.templates.env.globals["is_list"] = lambda x: isinstance(  # type: ignore
            x, list
        )
        self.templates.env.globals["get_object_identifier"] = get_object_identifier
        return self.templates

    @override
    async def login(self, request: Request) -> RedirectResponse | Response:
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


depends.set(Admin)
