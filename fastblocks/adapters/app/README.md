# App Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

> ⚠️ **Stale content:** This README still references the pre-0.13.x
> ACB-based architecture. ACB was removed in Phase 3.1; FastBlocks
> now uses Oneiric. See `docs/migrations/0.7-to-0.8.md` and
> `CLAUDE.md` for the current truth. Rewriting in progress.

The App adapter manages application configuration and initialization in FastBlocks.

## Relationship with Oneiric

The App adapter extends Oneiric's configuration system with web application specific settings:

- **Oneiric Foundation**: Provides the core configuration system and application settings structure
- **FastBlocks Extension**: Adds web-specific settings and integrates with Starlette/ASGI

The App adapter inherits from `OneiricSettings` and adds web-specific functionality.

## Overview

The App adapter provides settings for your application, including:

- Application name
- UI style (e.g., Kelp, Vanilla)
- Theme (light/dark)

## Template Variants

The App adapter ships with five named template variants under `fastblocks/adapters/app/_templates/`:

- `base/` — minimal baseline templates
- `bulma/` — Bulma CSS framework
- `fastblocks_ui/` — FastBlocks first-party UI components
- `kelp/` — Kelp UI library
- `vanilla/` — Vanilla CSS with semantic classes
- `webawesome/` — Web Awesome (Font Awesome 7)

The available variant directories are listed by `git ls-files fastblocks/adapters/app/_templates/`.

## Configuration

Configure the App adapter in your settings:

```yaml
# settings/app.yml
app:
  name: "MyApp"
  style: "vanilla"
  theme: "light"
```

## Usage

### Basic Access

```python
from oneiric.core.depends import depends
from fastblocks.core.resolver import resolve_component_async

# Module-level access
app = await resolve_component_async(depends, "fastblocks", "app")
app_name: str = app.settings.name
app_style: str = app.settings.style
app_theme: str = app.settings.theme
```

### Using in Route Handlers

```python
from oneiric.core.depends import depends
from fastblocks.core.resolver import resolve_component_async
from starlette.routing import Route

App = resolve_component(depends, "fastblocks", "app")
Templates = resolve_component(depends, "fastblocks", "templates")


@depends.inject
async def homepage(request, app=App, templates=Templates):
    """Homepage with app settings in context."""
    return await templates.app.render_template(
        request,
        "index.html",
        context={
            "app_name": app.settings.name,
            "app_style": app.settings.style,
            "app_theme": app.settings.theme,
        },
    )


@depends.inject
async def settings_page(request, app=App, templates=Templates):
    """Display current application settings."""
    return await templates.app.render_template(
        request,
        "settings.html",
        context={"app_settings": app.settings.model_dump()},
    )


routes = [
    Route("/", endpoint=homepage),
    Route("/settings", endpoint=settings_page),
]
```

### Using in Templates

App settings are automatically available in template context through the `app` variable:

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html data-theme="[[ app.theme ]]">
  <head>
    <title>[[ app.name ]]</title>
    [[ stylesheet_links() | safe ]]
  </head>
  <body>
    <nav class="navbar">
      <div class="navbar-brand">
        <span class="navbar-item">[[ app.name ]]</span>
      </div>
    </nav>

    [% block content %][% endblock %]

    <footer>
      <p>&copy; 2025 [[ app.name ]]</p>
    </footer>
  </body>
</html>
```

### Dynamic Theme Switching

```python
from oneiric.core.depends import depends
from fastblocks.core.resolver import resolve_component
from starlette.responses import RedirectResponse

App = resolve_component(depends, "fastblocks", "app")


@depends.inject
async def toggle_theme(request, app=App):
    """Toggle between light and dark theme."""
    current_theme = app.settings.theme

    # Update theme setting
    new_theme = "dark" if current_theme == "light" else "light"
    app.settings.theme = new_theme

    # Store preference in session
    request.session["theme"] = new_theme

    # Redirect back to referring page
    referer = request.headers.get("referer", "/")
    return RedirectResponse(referer, status_code=303)
```

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `name` | `str` | `"fastblocks"` | The name of your application |
| `style` | `str` | `"vanilla"` | The UI framework/style to use |
| `theme` | `str` | `"light"` | The color theme (light/dark) |

## Implementation Details

The App adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `default.py`: Provides the default implementation (renamed from the legacy default module).

### Base Class

```python
from oneiric.core.config import OneiricSettings


class AppBaseSettings(OneiricSettings):
    name: str = "fastblocks"
    style: str = "vanilla"
    theme: str = "light"


class AppBase: ...
```

## Customization

You can extend the App adapter with additional settings or functionality by creating a custom implementation:

```python
# myapp/adapters/app/custom.py
from fastblocks.adapters.app._base import AppBase, AppBaseSettings


class CustomAppSettings(AppBaseSettings):
    logo_url: str = "/static/logo.png"
    footer_text: str = "© 2025 My Company"


class CustomApp(AppBase):
    settings: CustomAppSettings | None = None

    async def init(self) -> None:
        # Custom initialization logic
        if self.settings is not None:
            self.logger.info(f"Initializing {self.settings.name} application")
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
app: custom
```
