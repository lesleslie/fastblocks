# Templates Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Templates adapter provides template rendering capabilities for FastBlocks applications.

## Overview

The Templates adapter allows you to:

- Render Jinja2 templates asynchronously
- Load templates from various sources (file system, cloud storage, Redis)
- Use template fragments for HTMX interactions
- Customize template delimiters and extensions

## Available Implementations

| Implementation | Description |
|----------------|-------------|
| `jinja2` | Asynchronous Jinja2 template engine |

## Configuration

Configure the Templates adapter in your settings:

```yaml
# settings/templates.yml
templates:
  loader: null  # Use default loader
  extensions:
    - "jinja2_fragments.FragmentExtension"
  delimiters:
    block_start_string: "[%"
    block_end_string: "%]"
    variable_start_string: "[["
    variable_end_string: "]]"
    comment_start_string: "[#"
    comment_end_string: "#]"
  globals:
    site_name: "My FastBlocks App"
    copyright_year: 2025
```

## Usage

### Basic Template Rendering

```python
from acb.depends import depends
from acb.adapters import import_adapter
from starlette.routing import Route

Templates = import_adapter("templates")
templates = depends.get(Templates)

async def homepage(request):
    context = {
        "title": "Welcome to FastBlocks",
        "message": "Hello, World!"
    }
    return await templates.app.render_template(
        request, "index.html", context=context
    )

routes = [
    Route("/", endpoint=homepage)
]
```

### Template Fragments for HTMX

FastBlocks is designed to work with HTMX and template fragments:

```python
async def get_user_list(request):
    users = await get_users_from_database()
    return await templates.app.render_template(
        request, "blocks/user_list.html", context={"users": users}
    )

routes = [
    Route("/block/user_list", endpoint=get_user_list)
]
```

In your main template:

```html
<div hx-get="/block/user_list" hx-trigger="load">
    Loading users...
</div>
```

And in your fragment template (`blocks/user_list.html`):

```html
<ul>
    [% for user in users %]
    <li>[[ user.username ]] - [[ user.email ]]</li>
    [% endfor %]
</ul>
```

## Template Loaders

The Templates adapter supports multiple template loaders:

- **FileSystemLoader**: Loads templates from the file system
- **CloudLoader**: Loads templates from cloud storage (S3, GCS, etc.)
- **RedisLoader**: Loads templates from Redis cache
- **PackageLoader**: Loads templates from Python packages

The loaders are tried in the following order:

1. **RedisLoader**: Fastest, used for cached templates
2. **CloudLoader**: Used for distributed deployments
3. **FileSystemLoader**: Used for local development

In development mode, the order is reversed to prioritize local file changes.

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `loader` | `Optional[str]` | `None` | Custom loader configuration |
| `extensions` | `list[str]` | `[]` | Jinja2 extensions to load |
| `delimiters` | `dict[str, str]` | See below | Custom delimiters for templates |
| `globals` | `dict[str, Any]` | `{}` | Global variables available in all templates |

Default delimiters:

```python
{
    "block_start_string": "[%",
    "block_end_string": "%]",
    "variable_start_string": "[[",
    "variable_end_string": "]]",
    "comment_start_string": "[#",
    "comment_end_string": "#]",
}
```

## Implementation Details

The Templates adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `jinja2.py`: Provides the Jinja2 implementation
- `_filters.py`: Defines custom template filters

### Base Class

```python
from acb.config import AdapterBase, Settings

class TemplatesBaseSettings(Settings):
    ...

class TemplatesBase(AdapterBase):
    ...
```

### Jinja2 Implementation

The Jinja2 implementation provides:

- **Asynchronous Rendering**: Templates are rendered asynchronously
- **Bytecode Caching**: Template bytecode is cached in Redis
- **Template Loaders**: Multiple loaders for different sources
- **Custom Delimiters**: Uses `[[` and `]]` for variables to avoid conflicts with JavaScript
- **Extensions**: Support for various Jinja2 extensions

## Template Filters

The Templates adapter includes several built-in filters:

- **`datetime`**: Format datetime objects
- **`filesize`**: Format file sizes
- **`truncate`**: Truncate text to a specific length
- **`markdown`**: Render Markdown text as HTML

You can add custom filters:

```python
from acb.depends import depends
from acb.adapters import import_adapter

Templates = import_adapter("templates")
templates = depends.get(Templates)

@templates.filter()
def uppercase(text: str) -> str:
    return text.upper()
```

## Customization

You can create a custom templates adapter for more specialized template needs:

```python
# myapp/adapters/templates/custom.py
from fastblocks.adapters.templates._base import TemplatesBase, TemplatesBaseSettings
from jinja2 import Environment, FileSystemLoader

class CustomTemplatesSettings(TemplatesBaseSettings):
    template_dir: str = "custom_templates"

class CustomTemplates(TemplatesBase):
    settings: CustomTemplatesSettings = None

    async def init(self) -> None:
        # Initialize custom template environment
        self.env = Environment(
            loader=FileSystemLoader(self.settings.template_dir),
            enable_async=True
        )

        # Add custom filters
        self.env.filters["custom_filter"] = self.custom_filter

    async def render_template(self, name: str, context: dict = None) -> str:
        template = self.env.get_template(name)
        return await template.render_async(**(context or {}))

    def custom_filter(self, value):
        # Custom filter implementation
        return value
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
templates: custom
```
