from contextlib import closing
from io import StringIO
from string import hexdigits

from acb import depends
from acb.actions.encode import load
from acb.adapters.cache import Cache
from acb.adapters.logger import Logger
from acb.config import Config
from acb.config import Settings
from acb.debug import debug
from aiopath import AsyncPath
from fastblocks import Request
from colour import web2hex  # type: ignore
from fastblocks.actions.minify import minify
from fastblocks.adapters.templates import Templates  # type: ignore


class StyleBaseSettings(Settings):
    ...


class StyleBase:
    cache: Cache = depends()  # type: ignore
    logger: Logger = depends()  # type: ignore
    config: Config = depends()  # type: ignore
    templates: Templates = depends()  # type: ignore

    @staticmethod
    def get_hex_color(color: str | int | None) -> str:
        if not color:
            return ""
        if str(color) == "0":
            color = "black"
        if all(c in hexdigits for c in str(color)):
            color = f"#{color}"
        return web2hex(color)

    @cache()  # type: ignore
    def remove_unused(self, html: str, index: int = 0) -> None:
        # selectors = include_selectors
        # if Request.path_params.startswith("/admin"):
        #     selectors = include_selectors + admin_include_selectors
        # p = minify.scss(html)
        # with suppress(IndexError):
        # inline = p.inlines[index]
        if self.config.debug.production or self.config.debug.style:
            self.logger.debug(f"Request path: {Request.path_params}")
            self.logger.debug(f"Remove unused css index: {index}")
            # self.logger.debug(f"CSS before: {len(inline.before.encode('utf-8'))}")
            # self.logger.debug(f"CSS after:  {len(inline.after.encode('utf-8'))}")
        # new_html = html.replace(inline.before, inline.after)
        # return new_html

    @cache()  # type: ignore
    def remove_old_vars(
        self, new_sass: dict[str, str], framework_sass: dict[str, str]
    ) -> dict[str, str]:
        remove = []
        for k in new_sass:
            if k not in framework_sass and k not in remove:
                remove.append(k)
                self.logger.debug(f"\tremoving old sass variable {k!r}")
        # pprint(remove)
        for r in remove:
            del new_sass[r]
        return new_sass

    @cache(expire=config.cache.default_timeout)  # type: ignore
    async def render_inline(self, path: AsyncPath, request: Request) -> str:
        with closing(StringIO()) as res:
            if self.config.deployed:
                default_yml = await self.templates.render_template(
                    path.name, request["context"]
                )
            else:
                default_yml = path.read_text()
            default_yml = load.yaml(default_yml)
            debug(default_yml)
            for k, v in default_yml.items():
                line = f"${k}: {v};\n"
                res.write(line)
            res.write(f"\n@import {self.config.style.path}/bulma.sass';")
            for extension in self.config.style.extensions:
                res.write(
                    f"\n@import '{self.config.style.extensions_dir}/"
                    f"{extension}/src/sass/index.sass';"
                )
            scss = [self.config.style.scss_path / self.config.style.theme_path]
            if "admin" in path.parts:
                scss.append(self.config.admin.scss.path)
            else:
                scss.extend(
                    [self.config.style.scss_path / self.config.style.theme_path]
                )
            for sass in scss:
                res.write(f"\n@import {sass!r};\n")
            res = res.getvalue()
        if self.config.debug.css:
            self.logger.debug(f"Style for {path.parent.parent}:\n{res}")
        # if not site.is_deployed or debug.production:
        res = minify.scss(res)
        return res
