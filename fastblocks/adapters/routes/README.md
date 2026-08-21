# Routes Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

> ⚠️ **Stale content:** This README still references the pre-0.13.x
> ACB-based architecture. ACB was removed in Phase 3.1; FastBlocks
> now uses Oneiric. See `docs/migrations/0.7-to-0.8.md` and
> `CLAUDE.md` for the current truth. Rewriting in progress.

The Routes adapter manages route discovery and registration in FastBlocks applications.

## Relationship with Oneiric

The Routes adapter is a FastBlocks-specific extension that uses Oneiric for component resolution:

- **Oneiric Foundation**: Provides component resolution, configuration loading, and dependency injection
- **FastBlocks Extension**: Implements web-specific route management for Starlette/ASGI

Unlike some other adapters, the Routes adapter is unique to FastBlocks. It uses the Oneiric resolver to integrate with other components like Templates and App.

## Overview

The Routes adapter allows you to:

- Define routes for your application
- Automatically discover routes from modules
- Create specialized endpoints for HTMX interactions

## Available Implementations

| Implementation | Description |
|----------------|-------------|
| `default` | Default routes implementation (`default.py`) |

## Usage

### Basic Setup

```python
from oneiric.core.depends import depends
from fastblocks.core.resolver import resolve_component, resolve_component_async
from fastblocks.applications import FastBlocks
from starlette.routing import Route

Templates = resolve_component(depends, "fastblocks", "templates")


@depends.inject
async def homepage(request, templates=Templates) -> object:
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )


# Define your routes
routes = [Route("/", endpoint=homepage)]

# Create your application
app = FastBlocks(routes=routes)

# Get the routes adapter
Routes = await resolve_component_async(depends, "fastblocks", "routes")
routes_adapter = depends.get(Routes)

# Access all routes
all_routes = routes_adapter.routes
```

### HTMX-Specific Endpoints

FastBlocks provides specialized endpoints for HTMX interactions:

```python
from fastblocks.adapters.routes.default import Index, Block
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
from oneiric.core.depends import depends
from fastblocks.core.resolver import resolve_component

Templates = resolve_component(depends, "fastblocks", "templates")


@depends.inject
async def about(request, templates=Templates) -> object:
    return await templates.app.render_template(request, "about.html")


routes = [Route("/about", endpoint=about)]
```

These routes will be automatically discovered and registered with your application.

## Implementation Details

The Routes adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `default.py`: Provides the default implementation (renamed from the legacy default module).

### Base Class

```python
from oneiric.core.config import OneiricSettings


class RoutesBaseSettings(OneiricSettings): ...


class RoutesBase: ...
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
from oneiric.core.depends import depends
from jinja2.exceptions import TemplateNotFound


class Index(HTTPEndpoint):
    @depends.inject
    async def get(self, request: t.Any, templates=Templates) -> Response:
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
from oneiric.core.depends import depends
from jinja2.exceptions import TemplateNotFound


class Block(HTTPEndpoint):
    @depends.inject
    async def get(self, request: t.Any, templates=Templates) -> Response:
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
        self.routes.extend(
            [
                Route("/favicon.ico", endpoint=self.favicon, methods=["GET"]),
                Route("/robots.txt", endpoint=self.robots, methods=["GET"]),
            ]
        )

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
