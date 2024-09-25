from acb.adapters import import_adapter
from acb.depends import depends
from asgi_htmx import HtmxRequest
from starlette.exceptions import HTTPException
from starlette.responses import PlainTextResponse


@depends.inject
async def handle_exception(request: HtmxRequest, exc: HTTPException):
    responses = {404: "Content not found", 500: "Server error"}
    templates = depends.get(import_adapter("templates"))
    if request.scope["htmx"]:
        return PlainTextResponse(
            content=responses[exc.status_code], status_code=exc.status_code
        )
    return await templates.app.render_template(
        request,
        "index.html",
        status_code=exc.status_code,
        context=dict(page=str(exc.status_code)),
    )
