import typing as t

from aiopath import AsyncPath
from jinja2.ext import debug as jinja_debug
from jinja2.ext import i18n
from jinja2.ext import loopcontrols
from jinja2_async_environment import AsyncEnvironment
from jinja2_async_environment import AsyncRedisBytecodeCache
from jinja2_async_environment import FileSystemLoader
from starlette.templating import pass_context
from starlette_async_jinja import AsyncJinja2Templates

jinja_env_configs = dict(
    block_start_string="[%",
    block_end_string="%]",
    variable_start_string="[[",
    variable_end_string="]]",
    comment_start_string="[#",
    comment_end_string="#]",
    extensions=[loopcontrols, i18n, jinja_debug],
    bytecode_cache=AsyncRedisBytecodeCache,
)


class Templates(AsyncJinja2Templates):
    def _create_env(
        self, directory: AsyncPath | t.Sequence[AsyncPath], **env_options: t.Any
    ) -> AsyncEnvironment:
        @pass_context  # type: ignore
        def url_for(context: dict[str, t.Any], name: str, **path_params: t.Any) -> str:
            request = context["request"]
            return request.url_for(name, **path_params)

        loader = FileSystemLoader(directory)
        env_options.setdefault("loader", loader)  # type: ignore
        env_options.setdefault("autoescape", True)
        env_options.setdefault("enable_async", True)
        env_options = jinja_env_configs | env_options
        env = AsyncEnvironment(**env_options)
        env.globals["url_for"] = url_for  # type: ignore
        return env


templates = Templates(directory=AsyncPath("templates"))
