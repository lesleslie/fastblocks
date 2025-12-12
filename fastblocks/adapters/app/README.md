# App Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The App adapter manages application configuration and initialization in FastBlocks.

## Relationship with ACB

The App adapter extends ACB's configuration system with web application specific settings:

- **ACB Foundation**: Provides the core configuration system and application settings structure
- **FastBlocks Extension**: Adds web-specific settings and integrates with Starlette/ASGI

The App adapter inherits from ACB's `AdapterBase` and extends `AppSettings` from ACB's configuration system, adding web-specific functionality while maintaining compatibility with ACB's core infrastructure.

## Overview

The App adapter provides settings for your application, including:

- Application name
- UI style (e.g., Bulma, Bootstrap)
- Theme (light/dark)

## Configuration

Configure the App adapter in your settings:

```yaml
# settings/app.yml
app:
  name: "MyApp"
  style: "bulma"
  theme: "light"
```

## Usage

### Basic Access

```python
from acb.depends import depends, Inject
from acb.adapters import import_adapter

App = import_adapter("app")

# Module-level access
app = depends.get(App)
app_name: str = app.settings.name
app_style: str = app.settings.style
app_theme: str = app.settings.theme
```

### Using in Route Handlers

```python
from acb.depends import depends, Inject
from acb.adapters import import_adapter
from starlette.routing import Route

App = import_adapter("app")
Templates = import_adapter("templates")


@depends.inject
async def homepage(request, app: Inject[App], templates: Inject[Templates]):
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
async def settings_page(request, app: Inject[App], templates: Inject[Templates]):
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

    [% if app.style == "bulma" %]
    <link
      rel="stylesheet"
      href="https://cdn.jsdelivr.net/npm/bulma@0.9.4/css/bulma.min.css"
    />
    [% elif app.style == "bootstrap" %]
    <link
      href="https://cdn.jsdelivr.net/npm/bootstrap@5.3.0/dist/css/bootstrap.min.css"
      rel="stylesheet"
    />
    [% endif %]
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
from acb.depends import depends, Inject
from acb.adapters import import_adapter
from starlette.responses import RedirectResponse

App = import_adapter("app")


@depends.inject
async def toggle_theme(request, app: Inject[App]):
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
| `style` | `str` | `"bulma"` | The UI framework/style to use |
| `theme` | `str` | `"light"` | The color theme (light/dark) |

## Implementation Details

The App adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `main.py`: Provides the default implementation

### Base Class

```python
from acb.config import AdapterBase
from acb.config import AppSettings as AppConfigSettings


class AppBaseSettings(AppConfigSettings):
    name: str = "fastblocks"
    style: str = "bulma"
    theme: str = "light"


class AppBase(AdapterBase): ...
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
