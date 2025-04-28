# App Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

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

```python
from acb.depends import depends
from acb.adapters import import_adapter

App = import_adapter("app")
app = depends.get(App)

# Access app settings
app_name: str = app.settings.name
app_style: str = app.settings.style
app_theme: str = app.settings.theme
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

class AppBase(AdapterBase):
    ...
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
