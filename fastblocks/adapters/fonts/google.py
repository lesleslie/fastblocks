from acb.depends import depends

from ._base import FontsBase
from ._base import FontsBaseSettings


class FontsSettings(FontsBaseSettings):
    primary: str = "Poppins"
    secondary: str = "Poppins"
    effects: dict[str, str] = {"primary": "3d-float"}


class Fonts(FontsBase): ...


depends.set(Fonts)


# @cache()
# def google_font(self, seq, user_agent):
#     family = google.fonts[seq].replace(" ", "+")
#     fonts = google.fonts.effects
#     if fonts and seq in fonts:
#         self.logger.info(
#             f"Fetching '{fonts[seq]}' effect from 'fonts.googleapis.com'..."
#         )
#         family = f"{family}&effect={fonts[seq]}"
#     self.logger.info(
#         f"Fetching '{google.fonts[seq]}' from 'fonts.googleapis.com'..."
#     )
#     font_css = self.cache.requests_session.get(
#         f"https://fonts.googleapis.com/css?family={family}",
#         headers={"User-Agent": user_agent},
#     ).text
#     font_css = font_css.replace(
#         "font-style: normal;", "font-style: normal;\n  font-display: swap;"
#     )
#     if debug.css or debug.cache:
#         self.cache.show_urls()
#     # if site.is_deployed or debug.production:
#     font_css = compress.scss(font_css)
#     return font_css
