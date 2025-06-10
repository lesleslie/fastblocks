# Templates Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Templates adapter provides template rendering capabilities for FastBlocks applications.

## Relationship with ACB

The Templates adapter is a FastBlocks-specific extension that builds on ACB's adapter pattern:

- **ACB Foundation**: Provides the adapter pattern, configuration loading, and dependency injection
- **FastBlocks Extension**: Implements template rendering specifically for web applications

Unlike some other adapters, the Templates adapter is unique to FastBlocks and doesn't have a direct counterpart in ACB. It leverages ACB's Storage adapter for template loading from various sources.

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

FastBlocks is designed to work seamlessly with HTMX for dynamic UI updates without full page reloads. The template system supports two approaches to fragments:

#### 1. Fragment Files

You can create separate template files for fragments:

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

#### 2. Named Template Blocks

You can also use named blocks within a single template file:

```python
async def get_user_details(request):
    user_id = request.path_params["user_id"]
    user = await get_user_from_database(user_id)

    # Render just the user_details block from the user_profile.html template
    return await templates.app.render_template_block(
        request,
        "user_profile.html",
        "user_details_block",
        context={"user": user}
    )

routes = [
    Route("/users/{user_id}/details", endpoint=get_user_details)
]
```

Template with named blocks (`user_profile.html`):

```html
[% block user_details_block %]
<div class="user-details">
    <h2>[[ user.full_name ]]</h2>
    <p><strong>Email:</strong> [[ user.email ]]</p>
    <p><strong>Joined:</strong> [[ user.joined_date | datetime("%B %d, %Y") ]]</p>
</div>
[% endblock %]

[% block user_stats_block %]
<div class="user-stats">
    <h3>Activity Stats</h3>
    <p><strong>Posts:</strong> [[ user.post_count ]]</p>
    <p><strong>Comments:</strong> [[ user.comment_count ]]</p>
</div>
[% endblock %]
```

### HTMX Integration Patterns

FastBlocks works particularly well with these HTMX patterns:

#### 1. Lazy Loading

Load content only when needed:

```html
<!-- Load user details when tab is clicked -->
<button
    hx-get="/users/123/details"
    hx-target="#user-details-container"
    hx-trigger="click">
    User Details
</button>

<div id="user-details-container"></div>
```

#### 2. Form Submission

Submit forms without page refresh:

```html
<form hx-post="/users/create" hx-swap="outerHTML">
    <input type="text" name="username" placeholder="Username">
    <input type="email" name="email" placeholder="Email">
    <button type="submit">Create User</button>
</form>
```

Server-side handler:

```python
async def create_user(request):
    form_data = await request.form()
    username = form_data.get("username")
    email = form_data.get("email")

    # Create user in database...

    # Return success message template fragment
    return await templates.app.render_template(
        request, "blocks/user_created.html",
        context={"username": username}
    )
```

#### 3. Real-time Search

Provide search results as the user types:

```html
<input
    type="search"
    name="q"
    placeholder="Search users..."
    hx-get="/users/search"
    hx-trigger="keyup changed delay:500ms"
    hx-target="#search-results">

<div id="search-results"></div>
```

#### 4. Infinite Scroll

Load more content when user scrolls to the bottom:

```html
<div id="user-list">
    <!-- Initial users loaded here -->
</div>

<div
    hx-get="/users?page=2"
    hx-trigger="revealed"
    hx-target="#user-list"
    hx-swap="beforeend">
    Loading more users...
</div>
```

### HTMX Response Headers

You can set HTMX-specific response headers to control client behavior:

```python
async def user_action(request):
    # Perform user action...

    response = await templates.app.render_template(
        request, "blocks/action_success.html"
    )

    # Set HTMX-specific headers
    response.headers["HX-Trigger"] = "userUpdated"  # Trigger client-side events
    response.headers["HX-Push-Url"] = "/users/profile"  # Update browser URL
    response.headers["HX-Redirect"] = "/dashboard"  # Redirect after request

    return response
```

For more information on HTMX integration, see the [official HTMX documentation](https://htmx.org/docs/).

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
from acb.config import  Settings

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
- **`minify_html`**: Minify HTML content
- **`minify_css`**: Minify CSS content
- **`minify_js`**: Minify JavaScript content
- **`map_src`**: URL-encode strings for use in URLs

### Using Built-in Filters

```html
<!-- Format a date -->
<p>Published: [[ article.published_date | datetime("%Y-%m-%d") ]]</p>

<!-- Format a file size -->
<p>Size: [[ file.size | filesize ]]</p>

<!-- Truncate text -->
<p>[[ article.content | truncate(100) ]]</p>

<!-- Render markdown -->
<div>[[ article.body | markdown ]]</div>

<!-- Minify inline CSS -->
<style>[[ styles | minify_css ]]</style>

<!-- Minify inline JavaScript -->
<script>[[ scripts | minify_js ]]</script>
```

### Creating Custom Filters

You can add custom filters in several ways:

#### 1. Using the filter decorator

```python
import typing as t
from acb.depends import depends
from acb.adapters import import_adapter

Templates = import_adapter("templates")
templates = depends.get(Templates)

@templates.filter()
def uppercase(text: str) -> str:
    """Convert text to uppercase."""
    return text.upper()

@templates.filter(name="reverse")
def reverse_text(text: str) -> str:
    """Reverse the characters in a string."""
    return text[::-1]
```

#### 2. Registering a filter function

```python
def pluralize(count: int, singular: str, plural: str = None) -> str:
    """Return singular or plural form based on count."""
    if count == 1:
        return singular
    if plural is None:
        return singular + "s"
    return plural

# Register the filter
templates.add_filter("pluralize", pluralize)
```

#### 3. Creating a filters module

For more complex scenarios, create a dedicated filters module:

```python
# myapp/templates/filters.py
import typing as t
from datetime import datetime

class CustomFilters:
    @staticmethod
    def relative_time(dt: datetime) -> str:
        """Format a datetime as a relative time string (e.g., '2 hours ago')."""
        now = datetime.now()
        diff = now - dt

        seconds = diff.total_seconds()
        if seconds < 60:
            return "just now"
        if seconds < 3600:
            minutes = int(seconds / 60)
            return f"{minutes} minute{'s' if minutes != 1 else ''} ago"
        if seconds < 86400:
            hours = int(seconds / 3600)
            return f"{hours} hour{'s' if hours != 1 else ''} ago"

        days = int(seconds / 86400)
        return f"{days} day{'s' if days != 1 else ''} ago"

# Then in your app initialization
from myapp.templates.filters import CustomFilters

for name in dir(CustomFilters):
    if not name.startswith("_") and callable(getattr(CustomFilters, name)):
        templates.add_filter(name, getattr(CustomFilters, name))
```

### Using Custom Filters in Templates

Once registered, you can use your custom filters in templates:

```html
<h1>[[ title | uppercase ]]</h1>
<p>[[ count | pluralize("item", "items") ]]</p>
<p>Posted [[ article.created_at | relative_time ]]</p>
```

## Customization

You can create a custom templates adapter for more specialized template needs:

```python
# myapp/adapters/templates/custom.py
import typing as t
from fastblocks.adapters.templates._base import TemplatesBase, TemplatesBaseSettings
from jinja2 import Environment, FileSystemLoader

class CustomTemplatesSettings(TemplatesBaseSettings):
    template_dir: str = "custom_templates"

class CustomTemplates(TemplatesBase):
    settings: CustomTemplatesSettings | None = None
    env: Environment | None = None

    async def init(self) -> None:
        # Initialize custom template environment
        if self.settings is not None:
            self.env = Environment(
                loader=FileSystemLoader(self.settings.template_dir),
                enable_async=True
            )

            # Add custom filters
            if self.env is not None:
                self.env.filters["custom_filter"] = self.custom_filter

    async def render_template(self, name: str, context: dict[str, t.Any] | None = None) -> str:
        if self.env is None:
            raise RuntimeError("Template environment not initialized")
        template = self.env.get_template(name)
        return await template.render_async(**(context or {}))

    def custom_filter(self, value: t.Any) -> t.Any:
        # Custom filter implementation
        return value
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
templates: custom
```
