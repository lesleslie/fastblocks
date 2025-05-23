from acb.depends import depends
from asgi_htmx import HtmxRequest
from starlette.exceptions import HTTPException
from starlette.requests import Request
from starlette.responses import PlainTextResponse, Response


async def handle_exception(request: HtmxRequest, exc: HTTPException):
    responses = {404: "Content not found", 500: "Server error"}
    templates = depends.get()
    status_code = getattr(exc, "status_code", 500)
    if request.scope["htmx"]:
        return PlainTextResponse(
            content=responses[status_code], status_code=status_code
        )
    return await templates.app.render_template(
        request,
        "index.html",
        status_code=status_code,
        context=dict(page=str(status_code)),
    )


class StarletteCachesException(Exception): ...


class DuplicateCaching(StarletteCachesException): ...


class MissingCaching(StarletteCachesException): ...


class RequestNotCachable(StarletteCachesException):
    def __init__(self, request: Request) -> None:
        super().__init__()
        self.request = request


class ResponseNotCachable(StarletteCachesException):
    def __init__(self, response: Response) -> None:
        super().__init__()
        self.response = response
