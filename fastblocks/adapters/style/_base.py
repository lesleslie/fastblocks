from contextlib import closing
from io import StringIO
from string import hexdigits

from acb.depends import depends
from acb.actions.encode import load
from acb.adapters import AdapterBase
from acb.adapters import import_adapter
from acb.config import Settings
from acb.debug import debug
from colour import web2hex  # type: ignore

from aiopath import AsyncPath
from asgi_htmx import HtmxRequest
from fastblocks.actions.minify import minify


Cache = import_adapter()
Templates = import_adapter()


class StyleBaseSettings(Settings): ...


class StyleBase(AdapterBase):
    cache: Cache = depends()  # type: ignore
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
            self.logger.debug(f"Request path: {HtmxRequest.path_params}")
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

    @cache()  # type: ignore
    async def render_inline(self, path: AsyncPath, request: HtmxRequest) -> str:
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
        # if not self.config.deployed or self.config.debug.production:
        res = minify.scss(res)
        return res
