
<p align="center">
<img src="./images/fastblocks-logo.png" alt="FastBlocks Logo">
</p>

> **FastBlocks Documentation**: [Main](./README.md) | [Core Features](./fastblocks/README.md) | [Actions](./fastblocks/actions/README.md) | [Adapters](./fastblocks/adapters/README.md)

# FastBlocks

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)


## What is FastBlocks?

FastBlocks is an asynchronous web application framework, inspired by FastAPI and built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines the power of modern Python async capabilities with the simplicity of server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

## Key Concepts

If you're new to FastBlocks, here are the key concepts to understand:

1. **Server-Side Rendering**: Unlike frameworks that rely heavily on JavaScript for interactivity, FastBlocks renders HTML on the server and sends only what's needed to the browser.

2. **HTMX**: A lightweight JavaScript library that allows you to access modern browser features directly from HTML, without writing JavaScript. FastBlocks is built with HTMX in mind.

3. **Template Blocks**: Small pieces of HTML that can be rendered independently and injected into the page, enabling dynamic updates without full page reloads.

4. **Adapters**: Pluggable components that provide standardized interfaces to different implementations (templates, authentication, admin interfaces, etc.).

5. **Dependency Injection**: A pattern that automatically provides components to your functions when needed, reducing boilerplate code.

6. **Asynchronous Architecture**: Built on Python's async/await syntax for high performance and efficient handling of concurrent requests.

## Key Features

- **Starlette Foundation**: Built on the [Starlette](https://www.starlette.io/) ASGI framework for high performance, extending its application class and middleware system
- **HTMX Integration**: First-class support for HTMX to create dynamic interfaces with server-side rendering
- **Asynchronous Architecture**: Built on [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), a modular framework providing dependency injection, configuration management, and pluggable components
- **Template-Focused**: Advanced asynchronous Jinja2 template system with fragments and partials support
- **Modular Design**: Pluggable adapters for authentication, admin interfaces, routing, and more
- **Performance Optimized**: Built-in Redis caching, Brotli compression, and HTML/CSS/JS minification
- **Type Safety**: Leverages Pydantic v2 for validation and type safety
- **Admin Interface**: Integrated SQLAlchemy Admin support for database management
- **Dependency Injection**: Simple yet powerful dependency injection system

## Table of Contents

- [Key Concepts](#key-concepts)
- [Installation](#installation)
- [Quick Start](#quick-start)
- [Common Patterns](#common-patterns)
- [Architecture Overview](#architecture-overview)
- [Core Components](#core-components)
  - [Templates](#templates)
  - [Routing](#routing)
  - [Middleware](#middleware)
  - [HTMX Integration](#htmx-integration)
- [Adapters](#adapters)
- [Actions](#actions)
- [Configuration](#configuration)
- [Command-Line Interface (CLI)](#command-line-interface-cli)
  - [Creating a New Project](#creating-a-new-project)
  - [Running Your Application](#running-your-application)
  - [CLI Options](#cli-options)
- [Examples](#examples)
- [Documentation](#documentation)
- [License](#license)
- [Acknowledgements](#acknowledgements)

## Installation

Install FastBlocks using [pdm](https://pdm.fming.dev):

```bash
pdm add fastblocks
```

### Requirements

- Python 3.13 or higher

### Optional Dependencies

FastBlocks supports various optional dependencies for different features:

| Feature Group | Components | Installation Command |
|---------------|------------|----------------------|
| Admin | SQLAlchemy Admin interface | `pdm add "fastblocks[admin]"` |
| Sitemap | Automatic sitemap generation | `pdm add "fastblocks[sitemap]"` |
| Monitoring | Sentry and Logfire integration | `pdm add "fastblocks[monitoring]"` |
| Complete | All dependencies | `pdm add "fastblocks[admin,sitemap,monitoring]"` |
| Development | Development tools | `pdm add -G dev "fastblocks"` |

You can also install FastBlocks using pip:

```bash
pip install fastblocks
```

For optional dependencies with pip:

```bash
pip install "fastblocks[admin,sitemap,monitoring]"
```

## Quick Start

Let's build a simple FastBlocks application step by step:

### 1. Create Your Application File

Create a file named `myapp.py` with the following code:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

# Import adapters - these are pluggable components that FastBlocks uses
# The Templates adapter handles rendering Jinja2 templates
# The App adapter provides the FastBlocks application instance
Templates = import_adapter("templates")  # Get the configured template adapter
App = import_adapter("app")  # Get the configured app adapter

# Define a route handler for the homepage
# The @depends.inject decorator automatically provides dependencies
@depends.inject
async def homepage(request, templates: Templates = depends()):
    # Render a template and return the response
    # This is similar to Flask's render_template but async
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )

# Define your application routes
routes = [
    Route("/", endpoint=homepage)  # Map the root URL to the homepage function
]

# Create a counter endpoint that demonstrates HTMX functionality
# This will handle both GET and POST requests
@depends.inject
async def counter_block(request, templates: Templates = depends()):
    # Get the current count from the session or default to 0
    count = request.session.get("count", 0)

    # If this is a POST request, increment the counter
    if request.method == "POST":
        count += 1
        request.session["count"] = count

    # Render just the counter block with the current count
    return await templates.app.render_template(
        request, "blocks/counter.html", context={"count": count}
    )

# Add the counter route
routes.append(Route("/block/counter", endpoint=counter_block, methods=["GET", "POST"]))

# Get the FastBlocks application instance
# This is pre-configured based on your settings
app = depends.get(App)
```

### 2. Create a Basic Template

Create a directory named `templates` and add a file named `index.html`:

```html
<!DOCTYPE html>
<html>
<head>
    <title>[[ title ]]</title>  <!-- FastBlocks uses [[ ]] instead of {{ }} for variables -->

    <!-- Include HTMX for interactivity without writing JavaScript -->
    <script src="https://unpkg.com/htmx.org@1.9.10" integrity="sha384-D1Kt99CQMDuVetoL1lrYwg5t+9QdHe7NLX/SoJYkXDFfX37iInKRy5xLSi8nO7UC" crossorigin="anonymous"></script>
</head>
<body>
    <h1>[[ title ]]</h1>

    <!--
    HTMX attributes explained:
    - hx-get: The URL to fetch when the element loads
    - hx-trigger: When to trigger the request (on load in this case)
    -->
    <div hx-get="/block/counter" hx-trigger="load">
        Loading counter...
    </div>

    <!--
    - hx-post: Send a POST request to this URL when clicked
    - hx-target: Update the previous div with the response
    -->
    <button hx-post="/block/counter" hx-target="previous div">
        Increment
    </button>
</body>
</html>
```

### 3. Create a Template Block

Create a directory named `templates/blocks` and add a file named `counter.html`:

```html
<div>
    <!-- This simple template will be rendered and returned for both GET and POST requests -->
    <h2>Counter: [[ count ]]</h2>
</div>
```

### 4. Create a Configuration File

Create a directory named `settings` and add a file named `app.yml`:

```yaml
app:
  name: "MyFastBlocksApp"
  title: "My First FastBlocks App"
  debug: true

# Configure session middleware
session:
  secret_key: "your-secret-key-here"  # In production, use a secure random key
  max_age: 14400  # Session timeout in seconds (4 hours)
```

### 5. Run Your Application

Run your application with Uvicorn:

```bash
uvicorn myapp:app --reload
```

Now visit http://localhost:8000 in your browser. You should see your page with a counter and an increment button. When you click the button, the counter will increment without a page reload - that's HTMX and FastBlocks working together!

## Common Patterns

Here are some common patterns and examples that will help you get started with FastBlocks:

### 1. Rendering Template Blocks for HTMX

One of the most common patterns in FastBlocks is rendering specific template blocks for HTMX requests:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def user_profile_block(request, templates: Templates = depends()):
    user_id = request.path_params["user_id"]

    # Fetch user data (in a real app, this would come from a database)
    user = {"id": user_id, "name": f"User {user_id}", "email": f"user{user_id}@example.com"}

    # Render just the user profile block
    return await templates.app.render_template_block(
        request,
        "users/profile.html",  # Template file
        "profile_block",       # Block name within the template
        context={"user": user}
    )

routes = [
    Route("/users/{user_id}/profile", endpoint=user_profile_block)
]
```

Template (`templates/users/profile.html`):

```html
{% block profile_block %}
<div class="user-profile">
    <h2>[[ user.name ]]</h2>
    <p>Email: [[ user.email ]]</p>
</div>
{% endblock %}
```

HTML with HTMX:

```html
<!-- Load user profile when button is clicked -->
<button hx-get="/users/123/profile" hx-target="#profile-container">
    Load Profile
</button>
<div id="profile-container"></div>
```

### 2. Form Submission with HTMX

Handling form submissions with HTMX is straightforward in FastBlocks:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def contact_form(request, templates: Templates = depends()):
    if request.method == "POST":
        # Get form data
        form_data = await request.form()
        name = form_data.get("name")
        email = form_data.get("email")
        message = form_data.get("message")

        # In a real app, you would save this to a database
        # For this example, we'll just return a success message

        # Return just the success message block
        return await templates.app.render_template_block(
            request,
            "contact/form.html",
            "success_block",
            context={"name": name}
        )

    # For GET requests, render the form
    return await templates.app.render_template(
        request,
        "contact/form.html",
        context={}
    )

routes = [
    Route("/contact", endpoint=contact_form, methods=["GET", "POST"])
]
```

Template (`templates/contact/form.html`):

```html
<!-- Main template content -->
<h1>Contact Us</h1>

<!-- Form that submits via HTMX -->
<form hx-post="/contact" hx-swap="outerHTML">
    <div class="form-group">
        <label for="name">Name:</label>
        <input type="text" id="name" name="name" required>
    </div>
    <div class="form-group">
        <label for="email">Email:</label>
        <input type="email" id="email" name="email" required>
    </div>
    <div class="form-group">
        <label for="message">Message:</label>
        <textarea id="message" name="message" required></textarea>
    </div>
    <button type="submit">Send Message</button>
</form>

<!-- Success message block that will replace the form -->
{% block success_block %}
<div class="success-message">
    <h2>Thank you, [[ name ]]!</h2>
    <p>Your message has been sent successfully.</p>
    <button hx-get="/contact" hx-target="this" hx-swap="outerHTML">Send Another Message</button>
</div>
{% endblock %}
```

### 3. Using Dependency Injection

FastBlocks leverages ACB's dependency injection system to make components easily accessible:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends
from acb.config import Config

# Import adapters
Templates = import_adapter("templates")
Cache = import_adapter("cache")

@depends.inject
async def dashboard(request,
                  templates: Templates = depends(),
                  cache: Cache = depends(),
                  config: Config = depends()):
    # Get cached data or compute it
    cache_key = "dashboard_stats"
    stats = await cache.get(cache_key)

    if not stats:
        # In a real app, you would fetch this from a database
        stats = {
            "users": 1250,
            "posts": 5432,
            "comments": 15876
        }

        # Cache the stats for 5 minutes
        await cache.set(cache_key, stats, ttl=300)

    # Get app name from configuration
    app_name = config.app.name

    return await templates.app.render_template(
        request,
        "dashboard.html",
        context={
            "app_name": app_name,
            "stats": stats
        }
    )

routes = [
    Route("/dashboard", endpoint=dashboard)
]
```

## Architecture Overview

### Relationship with Starlette

FastBlocks is built directly on top of [Starlette](https://www.starlette.io/), extending its capabilities for server-side rendered applications:

- **Class Extension**: The `FastBlocks` class extends Starlette's `Starlette` application class, inheriting all its core functionality

- **Enhanced Request Handling**: Extends Starlette's request handling with HTMX-specific features through the `HtmxRequest` class

- **Middleware Extensions**: Adds specialized middleware components on top of Starlette's middleware system

- **Template Integration**: Enhances Starlette with advanced template rendering capabilities

- **Error Handling**: Extends Starlette's exception handling with template-aware error responses

This approach allows FastBlocks to leverage Starlette's robust ASGI implementation while adding specialized features for server-side rendering and HTMX integration.

### Relationship with ACB

FastBlocks is built on top of [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), which provides the foundational architecture. The relationship can be summarized as:

- **Foundation vs. Framework**: ACB provides the core infrastructure (dependency injection, configuration, adapters pattern) while FastBlocks is a web application framework built on this foundation.

- **Dependency Chain**: User Application → FastBlocks → Starlette + ACB → Python Standard Library

- **Component Architecture**: FastBlocks extends ACB's component architecture with web-specific components like templates, routing, and HTMX integration.

- **Adapter Pattern**: FastBlocks uses ACB's adapter pattern to create pluggable components for authentication, admin interfaces, templates, etc.

This separation allows FastBlocks to focus on web application concerns while leveraging ACB's robust component architecture for the underlying infrastructure.

### Project Structure

FastBlocks follows a component-based architecture with automatic discovery and registration of modules:

```
fastblocks/
├── actions/         # Utility functions (minify)
├── adapters/        # Integration modules for external systems
│   ├── app/         # Application configuration
│   ├── auth/        # Authentication adapters
│   ├── admin/       # Admin interface adapters
│   ├── routes/      # Routing adapters
│   ├── sitemap/     # Sitemap generation
│   └── templates/   # Template engine adapters
├── applications.py  # FastBlocks application class
├── middleware.py    # ASGI middleware components
└── ...
```

## Core Components

### Templates

FastBlocks uses an enhanced asynchronous Jinja2 template system designed specifically for HTMX integration and server-side rendering.

#### Key Features

- **Async Template Loading**: Load templates asynchronously from file system, cloud storage, or Redis
- **Template Fragments**: Render specific blocks of templates for HTMX partial updates
- **Custom Delimiters**: Uses `[[` and `]]` for variables instead of `{{` and `}}` to avoid conflicts with JavaScript frameworks
- **Bytecode Caching**: Redis-based bytecode caching for improved performance
- **Built-in Filters**: Includes filters for minification, URL encoding, and more

#### Basic Template Usage

```python
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def homepage(request, templates: Templates = depends()):
    # Render a full template
    return await templates.app.render_template(
        request,
        "index.html",  # Template file path relative to templates directory
        context={"title": "FastBlocks Demo", "user": {"name": "John"}}
    )
```

#### Template Structure

FastBlocks templates use Jinja2 syntax with custom delimiters:

```html
<!DOCTYPE html>
<html>
<head>
    <title>[[ title ]]</title>  <!-- Note the [[ ]] delimiters instead of {{ }} -->
</head>
<body>
    <h1>Welcome, [[ user.name ]]!</h1>

    {% block content %}
    <p>This is the default content.</p>
    {% endblock %}
</body>
</html>
```

#### Template Inheritance

You can use Jinja2's template inheritance:

```html
<!-- templates/base.html -->
<!DOCTYPE html>
<html>
<head>
    <title>[[ title ]]</title>
    <link rel="stylesheet" href="/static/css/style.css">
    {% block head %}{% endblock %}
</head>
<body>
    <header>
        <nav><!-- Navigation --></nav>
    </header>

    <main>
        {% block content %}{% endblock %}
    </main>

    <footer>
        &copy; [[ current_year ]] FastBlocks Demo
    </footer>
</body>
</html>
```

```html
<!-- templates/home.html -->
{% extends "base.html" %}

{% block head %}
<script src="https://unpkg.com/htmx.org@1.9.10"></script>
{% endblock %}

{% block content %}
<h1>Welcome to [[ title ]]</h1>
<div id="counter-container" hx-get="/block/counter" hx-trigger="load">
    Loading...
</div>
{% endblock %}
```

#### Template Blocks for HTMX

Create template blocks specifically for HTMX responses:

```html
<!-- templates/blocks/counter.html -->
{% block counter_block %}
<div class="counter">
    <h2>Count: [[ count ]]</h2>
    <button hx-post="/block/counter" hx-target="#counter-container">Increment</button>
</div>
{% endblock %}
```

```python
@depends.inject
async def counter_block(request, templates: Templates = depends()):
    count = request.session.get("count", 0)
    if request.method == "POST":
        count += 1
        request.session["count"] = count

    # Render just the counter block
    return await templates.app.render_template_block(
        request,
        "blocks/counter.html",  # Template file
        "counter_block",        # Block name within the template
        context={"count": count}
    )
```

#### Custom Filters

FastBlocks includes several built-in filters and you can add your own:

```python
from acb.adapters import import_adapter

Templates = import_adapter("templates")

# Register a custom filter
@Templates.filter()
def capitalize_words(value: str) -> str:
    return " ".join(word.capitalize() for word in value.split())
```

Usage in templates:

```html
<h1>[[ user.name | capitalize_words ]]</h1>
```

#### Built-in Filters

FastBlocks includes several useful filters:

- **minify_html**: Minifies HTML content
- **minify_js**: Minifies JavaScript content
- **minify_css**: Minifies CSS content
- **map_src**: URL-encodes strings for use in URLs

### Routing

The routing system extends Starlette's routing with enhanced features for HTMX and server-side rendering.

#### Key Features

- **Automatic Route Discovery**: Routes are automatically discovered and registered
- **HTMX-Aware Endpoints**: Built-in support for HTMX requests and responses
- **Block Rendering**: Specialized endpoints for rendering template blocks

#### Basic Routing

FastBlocks supports Starlette's routing patterns with additional features:

```python
from starlette.routing import Route, Mount
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def homepage(request, templates: Templates = depends()):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )

@depends.inject
async def about(request, templates: Templates = depends()):
    return await templates.app.render_template(
        request, "about.html", context={"title": "About Us"}
    )

# Define your routes
routes = [
    Route("/", endpoint=homepage),
    Route("/about", endpoint=about),
    Mount("/static", StaticFiles(directory="static"), name="static"),
]
```

#### Route Discovery

FastBlocks can automatically discover and register routes from your application:

```python
# routes.py
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def homepage(request, templates: Templates = depends()):
    return await templates.app.render_template(
        request, "index.html", context={"title": "FastBlocks Demo"}
    )

# Export routes to be automatically discovered
routes = [
    Route("/", endpoint=homepage),
]
```

#### Path Parameters

You can use path parameters in your routes:

```python
@depends.inject
async def user_profile(request, templates: Templates = depends()):
    user_id = request.path_params["user_id"]
    # Fetch user data...
    return await templates.app.render_template(
        request, "user/profile.html", context={"user_id": user_id}
    )

routes = [
    Route("/users/{user_id}", endpoint=user_profile),
]
```

#### HTMX-Specific Routes

Create routes specifically for HTMX interactions:

```python
@depends.inject
async def load_more_items(request, templates: Templates = depends()):
    page = int(request.query_params.get("page", 1))
    # Fetch items for the requested page...
    items = [f"Item {i}" for i in range((page-1)*10, page*10)]

    # Return just the items block for HTMX to insert
    return await templates.app.render_template_block(
        request,
        "items.html",
        "items_block",
        context={"items": items, "page": page}
    )

routes = [
    Route("/api/items", endpoint=load_more_items),
]
```

### Middleware

FastBlocks includes several middleware components:

- **HTMX Middleware**: Adds HTMX-specific request information
- **CSRF Protection**: Built-in CSRF protection for forms
- **Session Middleware**: Cookie-based session management
- **Compression**: Brotli compression for reduced payload sizes
- **Secure Headers**: Security headers for production environments
- **Cache Middleware**: HTTP response caching with rule-based configuration
- **Cache Control Middleware**: Simplified management of cache control headers
- **Process Time Header Middleware**: Measures and logs request processing time
- **Current Request Middleware**: Makes the current request available via a context variable

### HTMX Integration

FastBlocks is designed to work seamlessly with HTMX, a lightweight JavaScript library that allows you to access modern browser features directly from HTML attributes.

#### Key HTMX Features in FastBlocks

- **HtmxRequest**: Extended request object with HTMX-specific attributes
- **Template Blocks**: Specialized endpoints for rendering template fragments
- **Push URL**: Automatic URL updates for browser history
- **Response Headers**: Helper methods for setting HTMX-specific response headers

#### Using HTMX Request Properties

FastBlocks extends Starlette's request object with HTMX-specific properties:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def product_detail(request, templates: Templates = depends()):
    product_id = request.path_params["product_id"]

    # Check if this is an HTMX request
    if request.htmx:
        # Access HTMX-specific properties
        is_boosted = request.htmx.boosted  # True if hx-boost was used
        trigger = request.htmx.trigger     # ID of the element that triggered the request
        target = request.htmx.target       # ID of the target element

        # For HTMX requests, render just the product details block
        return await templates.app.render_template_block(
            request,
            "products/detail.html",
            "product_detail_block",
            context={"product_id": product_id}
        )

    # For regular requests, render the full page
    return await templates.app.render_template(
        request,
        "products/detail.html",
        context={"product_id": product_id}
    )

routes = [
    Route("/products/{product_id}", endpoint=product_detail)
]
```

#### Setting HTMX Response Headers

FastBlocks makes it easy to set HTMX-specific response headers:

```python
from starlette.responses import Response
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def search_results(request, templates: Templates = depends()):
    query = request.query_params.get("q", "")

    # Render the search results
    response = await templates.app.render_template_block(
        request,
        "search/results.html",
        "results_block",
        context={"query": query, "results": []}
    )

    # Set HTMX-specific headers
    response.headers["HX-Push-Url"] = f"/search?q={query}"  # Update browser URL
    response.headers["HX-Trigger"] = "search-complete"      # Trigger client-side events

    return response

routes = [
    Route("/search", endpoint=search_results)
]
```

#### Common HTMX Patterns

Here are some common HTMX patterns you can use with FastBlocks:

- **Click to Load**: `<button hx-get="/more" hx-target="#content">Load More</button>`
- **Form Submission**: `<form hx-post="/submit" hx-swap="outerHTML">...</form>`
- **Infinite Scroll**: `<div hx-get="/next-page" hx-trigger="revealed" hx-swap="afterend"></div>`
- **Active Search**: `<input type="text" name="q" hx-get="/search" hx-trigger="keyup changed delay:500ms" hx-target="#results">`
- **Confirmation Dialog**: `<button hx-delete="/item/1" hx-confirm="Are you sure?">Delete</button>`

## Adapters

FastBlocks uses a pluggable adapter system for various components:

- **App**: Application configuration and initialization
- **Auth**: Authentication providers (Basic, etc.)
- **Admin**: Admin interface providers (SQLAdmin)
- **Routes**: Route management and discovery
- **Templates**: Template engine adapters (Jinja2)
- **Sitemap**: Sitemap generation

For more information about adapters, see the [Adapters Documentation](./fastblocks/adapters/README.md).

## Actions

Actions are utility functions that perform specific tasks:

- **Minify**: HTML, CSS, and JavaScript minification

For more information about actions, see the [Actions Documentation](./fastblocks/actions/README.md).

## Configuration

FastBlocks uses ACB's configuration system based on Pydantic, which provides a unified way to manage settings from multiple sources:

```python
from acb.config import Config
from acb.depends import depends

config = depends.get(Config)

# Access configuration values
secret_key = config.app.secret_key
debug_mode = config.debug.fastblocks
```

### Configuration Sources

- **YAML Files**: Environment-specific settings in YAML format (settings/app.yml, settings/debug.yml, etc.)
- **Secret Files**: Secure storage of sensitive information
- **Environment Variables**: Override configuration via environment variables

### FastBlocks-Specific Configuration

FastBlocks extends ACB's configuration system with web-specific settings for templates, routing, middleware, and more. These settings are automatically loaded and validated using Pydantic models.

## Command-Line Interface (CLI)

FastBlocks includes a powerful CLI tool to help you create and run applications.

### Installation

When you install FastBlocks, the CLI is automatically available:

```bash
python -m fastblocks --help
```

### Creating a New Project

Create a new FastBlocks project with the `create` command:

```bash
python -m fastblocks create
```

You'll be prompted for:
- **app_name**: Name of your application
- **style**: UI framework to use (bulma, webawesome, or custom)
- **domain**: Application domain

This will create a new directory with the following structure:

```
myapp/
├── __init__.py
├── .envrc
├── adapters/
│   └── __init__.py
├── actions/
│   └── __init__.py
├── main.py
├── models.py
├── pyproject.toml
├── routes.py
├── settings/
│   ├── adapters.yml
│   ├── app.yml
│   └── debug.yml
└── templates/
    ├── base/
    │   └── blocks/
    └── style/
        ├── blocks/
        └── theme/
```

### Running Your Application

Run your application in development mode with hot-reloading:

```bash
python -m fastblocks dev
```

Run your application in production mode:

```bash
python -m fastblocks run
```

Run your application with Granian (high-performance ASGI server):

```bash
python -m fastblocks dev --granian
```

Run your application in a Docker container:

```bash
python -m fastblocks run --docker
```

### CLI Options

#### Create Command

```bash
python -m fastblocks create --app-name myapp --style bulma --domain example.com
```

#### Dev Command

```bash
python -m fastblocks dev [--granian]
```

#### Run Command

```bash
python -m fastblocks run [--docker] [--granian]
```

## Examples

### Creating a Dynamic Counter with HTMX

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import depends

# Import adapters
Templates = import_adapter("templates")
App = import_adapter("app")

counter = 0

@depends.inject
async def get_counter(request, templates: Templates = depends()):
    return await templates.app.render_template(
        request, "blocks/counter.html", context={"count": counter}
    )

@depends.inject
async def increment_counter(request, templates: Templates = depends()):
    global counter
    counter += 1
    return await templates.app.render_template(
        request, "blocks/counter.html", context={"count": counter}
    )

routes = [
    Route("/block/counter", endpoint=get_counter, methods=["GET"]),
    Route("/block/counter", endpoint=increment_counter, methods=["POST"]),
]

# Create the application
app = depends.get(App)
```

## Documentation

For more detailed documentation about FastBlocks components:

- [**Core Features**](./fastblocks/README.md): Applications, middleware, and core functionality
- [**Actions**](./fastblocks/actions/README.md): Utility functions like minification
- [**Adapters**](./fastblocks/adapters/README.md): Pluggable components for various features
  - [**App Adapter**](./fastblocks/adapters/app/README.md): Application configuration
  - [**Auth Adapter**](./fastblocks/adapters/auth/README.md): Authentication providers
  - [**Admin Adapter**](./fastblocks/adapters/admin/README.md): Admin interface
  - [**Routes Adapter**](./fastblocks/adapters/routes/README.md): Routing system
  - [**Templates Adapter**](./fastblocks/adapters/templates/README.md): Template engine
  - [**Sitemap Adapter**](./fastblocks/adapters/sitemap/README.md): Sitemap generation
- [**Testing Guide**](./tests/README.md): Comprehensive guide to testing ACB components
- [**Running Tests**](./tests/TESTING.md): Instructions for running tests

## License

This project is licensed under the terms of the BSD 3-Clause license.

## Acknowledgements

Special thanks to the following open-source projects that power FastBlocks:

### Foundation
- [Starlette](https://www.starlette.io/) - The ASGI framework that FastBlocks directly extends, providing the web application foundation
- [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb) - The core infrastructure providing dependency injection, configuration, and component architecture

### Frontend & Templates
- [HTMX](https://htmx.org/) - The lightweight JavaScript library for dynamic interfaces
- [Jinja2](https://jinja.palletsprojects.com/) - The template engine
- [jinja2-async-environment](https://github.com/lesleslie/jinja2-async-environment) - Asynchronous Jinja2 environment
- [starlette-async-jinja](https://github.com/lesleslie/starlette-async-jinja) - Starlette integration for async Jinja2

### Data & Validation
- [Pydantic](https://pydantic-docs.helpmanual.io/) - Data validation and settings management
- [SQLAlchemy](https://www.sqlalchemy.org/) - SQL toolkit and ORM
