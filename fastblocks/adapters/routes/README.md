# Routes Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Routes adapter manages route discovery and registration in FastBlocks applications.

## Relationship with ACB

The Routes adapter is a FastBlocks-specific extension that builds on ACB's adapter pattern:

- **ACB Foundation**: Provides the adapter pattern, configuration loading, and dependency injection
- **FastBlocks Extension**: Implements web-specific route management for Starlette/ASGI

Unlike some other adapters, the Routes adapter is unique to FastBlocks and doesn't have a direct counterpart in ACB. It uses ACB's dependency injection system to integrate with other components like Templates and App.

## Overview

The Routes adapter allows you to:

- Define routes for your application
- Automatically discover routes from modules
- Create specialized endpoints for HTMX interactions

## Available Implementations

| Implementation | Description |
|----------------|-------------|
| `default` | Default routes implementation |

## Usage

### Basic Setup

```python
from acb.depends import depends
from acb.adapters import import_adapter
from fastblocks.applications import FastBlocks
from starlette.routing import Route

async def homepage(request) -> object:
    return await request.app.templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )

# Define your routes
routes = [
    Route("/", endpoint=homepage)
]

# Create your application
app = FastBlocks(routes=routes)

# Get the routes adapter
Routes = import_adapter("routes")
routes_adapter = depends.get(Routes)

# Access all routes
all_routes = routes_adapter.routes
```

### HTMX-Specific Endpoints

FastBlocks provides specialized endpoints for HTMX interactions:

```python
from fastblocks.adapters.routes.main import Index, Block
from starlette.routing import Route

# Index endpoint handles both full page and HTMX partial requests
routes = [
    Route("/", Index, methods=["GET"]),
    Route("/{page}", Index, methods=["GET"]),

    # Block endpoint for rendering template blocks
    Route("/block/{block}", Block, methods=["GET"]),
]
```

### Automatic Route Discovery

The Routes adapter can automatically discover routes from modules:

```python
# myapp/routes.py
from starlette.routing import Route

async def about(request) -> object:
    return await request.app.templates.app.render_template(
        request, "about.html"
    )

routes = [
    Route("/about", endpoint=about)
]
```

These routes will be automatically discovered and registered with your application.

## Implementation Details

The Routes adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `main.py`: Provides the default implementation

### Base Class

```python
from acb.config import  Settings

class RoutesBaseSettings(Settings):
    ...

class RoutesBase(AdapterBase):
    ...
```

### Default Implementation

The default implementation provides:

- **Index Endpoint**: Handles both full page and HTMX partial requests
- **Block Endpoint**: Renders template blocks for HTMX interactions
- **Route Discovery**: Automatically discovers routes from modules
- **Standard Routes**: Provides standard routes for favicon.ico and robots.txt

## Built-in Endpoints

### Index Endpoint

The `Index` endpoint handles both full page and HTMX partial requests:

```python
import typing as t
from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response
from starlette.exceptions import HTTPException
from acb.depends import depends
from acb.config import Config
from jinja2.exceptions import TemplateNotFound

class Index(HTTPEndpoint):
    config: Config = depends()
    templates: t.Any = depends()

    async def get(self, request: t.Any) -> Response:
        page = request.path_params.get("page") or "home"
        template = "index.html"
        headers = dict(vary="hx-request")
        if htmx := request.scope["htmx"]:
            template = f"{page.lstrip('/')}.html"
            headers["hx-push-url"] = "/" if page == "home" else page
        try:
            return await self.templates.app.render_template(
                request, template, headers=headers, context=dict(page=page.lstrip("/"))
            )
        except TemplateNotFound:
            raise HTTPException(status_code=404)
```

### Block Endpoint

The `Block` endpoint renders template blocks for HTMX interactions:

```python
import typing as t
from starlette.endpoints import HTTPEndpoint
from starlette.responses import Response
from starlette.exceptions import HTTPException
from acb.depends import depends
from jinja2.exceptions import TemplateNotFound

class Block(HTTPEndpoint):
    templates: t.Any = depends()

    async def get(self, request: t.Any) -> Response:
        block = f"blocks/{request.path_params['block']}.html"
        try:
            return await self.templates.app.render_template(request, block)
        except TemplateNotFound:
            raise HTTPException(status_code=404)
```

## Customization

You can create a custom routes adapter for more specialized routing needs:

```python
# myapp/adapters/routes/custom.py
import typing as t
from fastblocks.adapters.routes._base import RoutesBase, RoutesBaseSettings
from starlette.routing import Route, Router, Mount, Host, WebSocketRoute

class CustomRoutesSettings(RoutesBaseSettings):
    api_prefix: str = "/api"

class CustomRoutes(RoutesBase):
    settings: CustomRoutesSettings | None = None
    routes: list[Route | Router | Mount | Host | WebSocketRoute] = []

    async def init(self) -> None:
        # Add standard routes
        self.routes.extend([
            Route("/favicon.ico", endpoint=self.favicon, methods=["GET"]),
            Route("/robots.txt", endpoint=self.robots, methods=["GET"]),
        ])

        # Add API routes with prefix
        api_routes = [
            Route("/users", endpoint=self.list_users, methods=["GET"]),
            Route("/users/{id:int}", endpoint=self.get_user, methods=["GET"]),
        ]
        if self.settings is not None:
            self.routes.append(Mount(self.settings.api_prefix, routes=api_routes))
        else:
            self.routes.append(Mount("/api", routes=api_routes))

        # Discover additional routes
        await self.discover_routes()
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
routes: custom
```
