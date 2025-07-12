
<p align="center">
<img src="./images/fastblocks-logo.png" alt="FastBlocks Logo">
</p>

> **FastBlocks Documentation**: [Main](./README.md) | [Core Features](./fastblocks/README.md) | [Actions](./fastblocks/actions/README.md) | [Adapters](./fastblocks/adapters/README.md)

# FastBlocks

[![Code style: crackerjack](https://img.shields.io/badge/code%20style-crackerjack-000042)](https://github.com/lesleslie/crackerjack)
[![Python: 3.13+](https://img.shields.io/badge/python-3.13%2B-green)](https://www.python.org/downloads/)
[![License: BSD-3-Clause](https://img.shields.io/badge/License-BSD_3--Clause-blue.svg)](https://opensource.org/licenses/BSD-3-Clause)


## What is FastBlocks?

FastBlocks is an asynchronous web application framework, inspired by FastAPI and built on Starlette, specifically designed for the rapid delivery of server-side rendered HTMX/Jinja template blocks. It combines modern Python async capabilities with server-side rendering to create dynamic, interactive web applications with minimal JavaScript.

Unlike monolithic frameworks or micro-frameworks that require extensive configuration, FastBlocks offers a modular, component-based architecture that provides batteries-included functionality while maintaining exceptional flexibility. Its adapter pattern allows for seamless component swapping, cloud provider migrations, and tailored customizations without extensive code changes.

## Key Concepts

If you're new to FastBlocks, here are the key concepts to understand:

1. **Server-Side Rendering**: Unlike frameworks that rely heavily on JavaScript for interactivity, FastBlocks renders HTML on the server and sends only what's needed to the browser.

2. **HTMX**: A lightweight JavaScript library that allows you to access modern browser features directly from HTML, without writing JavaScript. FastBlocks is built with HTMX in mind.

3. **Template Blocks**: Small pieces of HTML that can be rendered independently and injected into the page, enabling dynamic updates without full page reloads.

4. **Adapters**: Pluggable components that provide standardized interfaces to different implementations (templates, authentication, admin interfaces, etc.). This architecture facilitates seamless provider switching, multi-cloud deployments, and targeted customizations without restructuring your application.

5. **Dependency Injection**: A pattern that automatically provides components to your functions when needed, reducing boilerplate code.

6. **Asynchronous Architecture**: Built on Python's async/await syntax for high performance and efficient handling of concurrent requests.

## Key Features

- **Starlette Foundation**: Built on the [Starlette](https://www.starlette.io/) ASGI framework for high performance, extending its application class and middleware system
- **HTMX Integration**: First-class support for HTMX to create dynamic interfaces with server-side rendering
- **Asynchronous Architecture**: Built on [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb), providing dependency injection, configuration management, and pluggable components
- **Template-Focused**: Advanced asynchronous Jinja2 template system with fragments and partials support using `[[` and `]]` delimiters
- **Modular Design**: Pluggable adapters for authentication, admin interfaces, routing, templates, and sitemap generation
- **Cloud Flexibility**: Easily switch between cloud providers or create hybrid deployments by swapping adapters
- **Performance Optimized**: Built-in caching system, Brotli compression, and HTML/CSS/JS minification
- **Type Safety**: Leverages Pydantic v2 for validation and type safety throughout
- **Admin Interface**: Integrated SQLAlchemy Admin support for database management
- **Dependency Injection**: Robust dependency injection system with automatic resolution
- **Batteries Included, But Replaceable**: Comprehensive defaults with the ability to customize or replace any component

## Why Choose FastBlocks?

FastBlocks stands out from other Python web frameworks through its unique combination of server-side rendering focus, component-based architecture, and hybrid cloud capabilities. Here's how FastBlocks compares to other popular frameworks:

### FastBlocks vs. FastAPI

While FastAPI excels at API development, FastBlocks is specifically designed for server-side rendered applications with HTMX:

| Aspect | FastBlocks | FastAPI |
|--------|------------|---------|
| **Primary Focus** | Server-side rendering + HTMX | JSON APIs + OpenAPI |
| **Template System** | Built-in async Jinja2 with HTMX support | External template engines required |
| **Component Architecture** | Pluggable adapters for all components | Manual dependency injection setup |
| **Cloud Flexibility** | Built-in adapter system for multi-cloud | Cloud integration requires custom solutions |
| **Frontend Approach** | HTMX for dynamic interfaces | Requires separate frontend framework |
| **Development Speed** | Rapid HTML-first development | Fast API development, slower frontend integration |
| **SEO Support** | Native server-side rendering | Requires additional SSR setup |
| **Learning Curve** | Simple HTML + Python | API design + frontend framework |

**Choose FastBlocks when:** You want to build interactive web applications with server-side rendering, need rapid development of admin interfaces, or prefer keeping business logic on the server.

**Choose FastAPI when:** You're building APIs for mobile apps, need extensive OpenAPI documentation, or are creating microservices.

### FastBlocks vs. FastHTML

FastHTML focuses on Python-in-HTML, while FastBlocks uses a traditional template-based approach:

| Aspect | FastBlocks | FastHTML |
|--------|------------|----------|
| **Template Approach** | Jinja2 templates with custom delimiters | Python functions generate HTML |
| **Separation of Concerns** | Clear separation of logic and presentation | Logic and presentation mixed |
| **Designer Collaboration** | HTML/CSS designers can work directly | Requires Python knowledge for frontend |
| **Template Ecosystem** | Full Jinja2 ecosystem and tooling | Limited to Python HTML generation |
| **Component Reusability** | Template blocks and inheritance | Python function composition |
| **Infrastructure Flexibility** | Adapter pattern for all components | Monolithic approach |
| **Cloud Deployment** | Built-in multi-cloud support | Manual cloud configuration |
| **Performance** | Async template caching and optimization | Runtime HTML generation |

**Choose FastBlocks when:** You work with designers, need template reusability, want infrastructure flexibility, or prefer traditional template-based development.

**Choose FastHTML when:** You prefer Python-only development, want inline HTML generation, or are building simple prototypes.

### FastBlocks vs. FastHX

FastHX provides HTMX utilities for FastAPI, while FastBlocks is a complete framework built around HTMX:

| Aspect | FastBlocks | FastHX |
|--------|------------|--------|
| **Framework Scope** | Complete web framework | HTMX utilities for FastAPI |
| **Template Integration** | Built-in async template system | Requires separate template setup |
| **Component Architecture** | Full adapter system | Limited to HTMX helpers |
| **Cloud Deployment** | Built-in multi-cloud adapters | Relies on FastAPI deployment |
| **Development Workflow** | Integrated HTMX + templates | Add-on to existing FastAPI |
| **Performance Optimization** | Built-in caching, compression, minification | Manual optimization required |
| **Admin Interface** | Integrated admin system | External admin interface needed |
| **Configuration Management** | ACB-based configuration system | FastAPI configuration |

**Choose FastBlocks when:** You want a complete HTMX-focused framework, need built-in admin interfaces, or want comprehensive infrastructure adapters.

**Choose FastHX when:** You have an existing FastAPI application and want to add HTMX capabilities incrementally.

### FastBlocks vs. FastHTMX

FastHTMX is another HTMX integration library, while FastBlocks is a complete framework:

| Aspect | FastBlocks | FastHTMX |
|--------|------------|----------|
| **Architecture** | Complete framework with adapters | HTMX integration library |
| **Template System** | Advanced async Jinja2 with fragments | Basic template integration |
| **Infrastructure** | Pluggable adapters for everything | Manual infrastructure setup |
| **Cloud Support** | Built-in multi-cloud capabilities | External cloud configuration |
| **Development Tools** | Full CLI, project generation, testing | Limited tooling |
| **Performance Features** | Caching, compression, minification | Basic HTMX support |
| **Admin Interface** | Integrated SQLAlchemy admin | No admin interface |
| **Dependency Injection** | ACB-based DI system | Manual dependency management |

**Choose FastBlocks when:** You want a batteries-included framework, need enterprise-grade features, or want rapid application development.

**Choose FastHTMX when:** You need a lightweight HTMX integration for an existing application.

### FastBlocks vs. Litestar

Litestar is a modern FastAPI alternative with native HTMX support, while FastBlocks focuses on server-side rendering:

| Aspect | FastBlocks | Litestar |
|--------|------------|----------|
| **Primary Focus** | Server-side rendering + HTMX | High-performance APIs |
| **Template System** | Built-in async templates with HTMX | External template engines |
| **HTMX Support** | Built-in HTMX integration | Native HTMX support |
| **Component Architecture** | Adapter pattern for flexibility | Plugin system |
| **Cloud Deployment** | Built-in multi-cloud adapters | Manual cloud integration |
| **Performance** | Optimized for SSR and HTMX | Optimized for API throughput |
| **Frontend Integration** | HTMX-first approach | API-first, frontend agnostic |
| **Development Experience** | HTML-first rapid development | Type-safe API development |
| **Infrastructure Flexibility** | Adapter-based infrastructure | Plugin-based extensions |

**Choose FastBlocks when:** You're building traditional web applications, need HTMX integration, or want infrastructure flexibility through adapters.

**Choose Litestar when:** You need high-performance APIs, want extensive type safety, or are building API-first applications.

### Key Advantages of FastBlocks

#### 🧩 **Component-Based Architecture**
- **Batteries Included, But Customizable**: Comprehensive defaults for rapid development, with every component easily replaceable
- **Pluggable Adapters**: Every component (auth, admin, templates, storage, cache) can be swapped without code changes
- **Consistent Interfaces**: Standardized APIs across all adapters ensure predictable behavior
- **Independent Evolution**: Update or replace individual components without affecting the entire application
- **Zero Lock-in**: Unlike monolithic frameworks, you're never locked into specific implementations

#### 🌐 **Multi-Cloud & Hybrid Deployment Ready**
- **Cloud Provider Flexibility**: Switch between AWS, Azure, GCP, or on-premise with configuration changes
- **Vendor Lock-in Prevention**: Abstract cloud-specific APIs behind adapter interfaces
- **Hybrid Strategies**: Mix and match services from different providers in the same application
- **Infrastructure as Code**: Configuration-driven infrastructure decisions

#### 🚀 **Server-Side Rendering Excellence**
- **HTMX-Native**: Built specifically for HTMX patterns and server-side rendering
- **Template Block Rendering**: Render specific template fragments for dynamic updates
- **SEO Optimized**: Full server-side rendering ensures search engine visibility
- **Progressive Enhancement**: Start with functional HTML, enhance with HTMX

#### ⚡ **Performance Optimized**
- **Async Everything**: Fully asynchronous template loading, caching, and rendering
- **Built-in Caching**: Redis-based template and response caching with configurable rules
- **Compression**: Brotli compression reduces payload sizes
- **Minification**: Built-in HTML, CSS, and JS minification

#### 🛠 **Developer Experience**
- **Rapid Development**: HTML-first approach with powerful template system
- **Full CLI**: Project generation, development server, testing, and deployment tools
- **Type Safety**: Pydantic-based configuration and validation throughout
- **Testing Support**: Comprehensive testing utilities and mocking framework

#### 🏢 **Enterprise Ready**
- **Configuration Management**: Multi-environment configuration with secrets management
- **Security Built-in**: CSRF protection, secure headers, session management
- **Admin Interface**: Integrated SQLAlchemy admin for database management
- **Monitoring**: Built-in integration with Sentry and Logfire
- **Deployment Options**: Docker, traditional servers, and cloud platforms

### When to Choose FastBlocks

FastBlocks is the ideal choice for:

- **Traditional Web Applications**: Where server-side rendering and SEO matter
- **Admin Dashboards**: Complex business logic with moderate UI complexity
- **Content Management Systems**: Where initial load performance is critical
- **Internal Tools**: Rapid development and maintenance are prioritized
- **Multi-Cloud Environments**: Organizations needing infrastructure flexibility
- **Team Collaboration**: Designers can work with HTML/CSS while developers handle Python logic
- **Prototype to Production**: Rapid prototyping that scales to enterprise needs

FastBlocks combines the development speed of modern frameworks with the infrastructure flexibility needed for enterprise deployment. Unlike monolithic frameworks that lock you into specific implementations, FastBlocks provides comprehensive defaults (batteries included) while maintaining the flexibility to customize or replace any component to suit your specific needs. This makes it an excellent choice for teams that want to move fast without sacrificing long-term flexibility or architectural control.

## Table of Contents

- [Why Choose FastBlocks?](#why-choose-fastblocks)
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
- [Migration Guide](#migration-guide)
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

# Import adapters using the new direct import pattern
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

**Note**: This example uses the new v0.13.2+ import patterns. The template system automatically handles dependency resolution with fallbacks, so if cache is unavailable, the function will still work correctly.

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

#### Direct ACB Integration (v0.13.2+)

Recent improvements include simplified dependency management through direct ACB imports:

```python
# Direct ACB imports for better performance
from acb.adapters import import_adapter
from acb.depends import depends
from acb.config import Config

# Get adapters directly from ACB
Templates = import_adapter("templates")
App = import_adapter("app")

# Access configuration and dependencies
config = depends.get(Config)
```

**Benefits of Direct Integration:**

- **Performance**: Eliminates wrapper overhead for faster adapter access
- **Type Safety**: Better type annotations and IDE support
- **Error Handling**: Enhanced error recovery with automatic fallbacks
- **Maintainability**: Aligned with ACB patterns for easier maintenance
- **Future-Proof**: Direct compatibility with ACB framework evolution

This separation allows FastBlocks to focus on web application concerns while leveraging ACB's robust component architecture for the underlying infrastructure.

### Server-Side Rendering with HTMX

FastBlocks is particularly well-suited for modern server-side rendering applications that use HTMX, offering several advantages over traditional approaches:

- **Reduced Complexity**: Avoid complex client-side state management and JavaScript frameworks
- **Improved Performance**: Server-side rendering can deliver faster initial page loads and smaller payloads
- **SEO-Friendly**: Fully rendered HTML content for better search engine optimization
- **Progressive Enhancement**: Start with functional HTML and enhance with HTMX for interactivity
- **Simplified Architecture**: Keep business logic on the server where it belongs
- **Reduced Development Time**: Use HTML templates and simple endpoints instead of complex API design

The combination of FastBlocks' templating system and HTMX offers a modern alternative to complex SPA frameworks, particularly for:

- **Admin dashboards**: Where business logic complexity outweighs UI complexity
- **Content management systems**: Where SEO and initial load performance are critical
- **Internal tools**: Where development speed and maintainability are prioritized over cutting-edge UIs
- **Applications with complex business logic**: Where keeping logic on the server simplifies testing and validation

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
- **Null Safety**: Enhanced dependency resolution with automatic fallbacks for missing components
- **Error Recovery**: Graceful handling of cache, storage, and dependency failures

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

#### Enhanced Dependency Resolution

Version 0.13.2 introduces robust dependency resolution with automatic fallbacks:

```python
from acb.adapters import import_adapter
from acb.depends import depends

Templates = import_adapter("templates")

@depends.inject
async def my_view(request, templates: Templates = depends()):
    # FastBlocks automatically handles:
    # 1. Primary dependency resolution via depends.get()
    # 2. Fallback to get_adapter() if primary fails
    # 3. Null safety checks throughout the template system
    # 4. Graceful error handling for missing dependencies

    return await templates.app.render_template(
        request, "my_template.html", context={"data": "value"}
    )
```

The template system now includes:

- **Automatic Fallbacks**: If cache or storage dependencies are unavailable, the system continues with file-based templates
- **Null Safety**: All operations check for null dependencies and provide sensible defaults
- **Error Recovery**: Template loading failures are handled gracefully with meaningful error messages
- **Dependency Order**: `depends.get()` is tried first, followed by `get_adapter()` fallback

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

#### Middleware Ordering

FastBlocks uses a position-based middleware system to ensure middleware components are executed in the correct order. The middleware execution flow follows the ASGI specification:

1. The last middleware in the list is the first to process the request
2. The first middleware in the list is the last to process the request

The actual execution flow is:
- ExceptionMiddleware (outermost - first to see request, last to see response)
- System middleware (ordered by MiddlewarePosition enum)
- User-provided middleware
- ServerErrorMiddleware (innermost - last to see request, first to see response)

#### Adding Custom Middleware

You can add custom middleware to your FastBlocks application in two ways:

1. **User Middleware**: Added to the user middleware stack

```python
# Add a middleware to the end of the user middleware stack
app.add_middleware(CustomMiddleware, option="value")

# Add a middleware at a specific position in the user middleware stack
app.add_middleware(CustomMiddleware, position=0, option="value")
```

2. **System Middleware**: Replace middleware at specific positions defined by the MiddlewarePosition enum

```python
from fastblocks.middleware import MiddlewarePosition

# Replace the compression middleware with a custom implementation
app.add_system_middleware(
    CustomMiddleware,
    position=MiddlewarePosition.COMPRESSION,
    option="value"
)
```

#### Example: Custom Middleware

Here's a complete example of creating and adding custom middleware:

```python
from typing import Any
from starlette.types import ASGIApp, Receive, Scope, Send
from fastblocks import FastBlocks
from fastblocks.middleware import MiddlewarePosition

# Define a simple custom middleware
class CustomHeaderMiddleware:
    """A middleware that adds a custom header to responses."""

    def __init__(self, app: ASGIApp, header_name: str, header_value: str) -> None:
        self.app = app
        self.header_name = header_name
        self.header_value = header_value

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        if scope["type"] != "http":
            await self.app(scope, receive, send)
            return

        async def send_with_header(message: dict[str, Any]) -> None:
            if message["type"] == "http.response.start":
                headers = message.get("headers", [])
                headers.append(
                    (self.header_name.encode(), self.header_value.encode())
                )
                message["headers"] = headers
            await send(message)

        await self.app(scope, receive, send_with_header)

# Create a FastBlocks application
app = FastBlocks()

# Add a custom middleware to the user middleware stack
app.add_middleware(
    CustomHeaderMiddleware,
    header_name="X-Custom-User",
    header_value="User-defined"
)

# Replace the compression middleware with a custom implementation
app.add_system_middleware(
    CustomHeaderMiddleware,
    position=MiddlewarePosition.COMPRESSION,
    header_name="X-Custom-Compression",
    header_value="Replaced"
)
```

#### Middleware Positions

The `MiddlewarePosition` enum defines the positions of middleware in the system stack:

```python
class MiddlewarePosition(IntEnum):
    # Core middleware (always present)
    PROCESS_TIME = 0      # First middleware to see request, last to see response
    CSRF = 1              # Security middleware should be early in the chain
    SESSION = 2           # Session handling (if auth enabled)
    HTMX = 3              # HTMX request processing
    CURRENT_REQUEST = 4   # Request context tracking
    COMPRESSION = 5       # Response compression
    SECURITY_HEADERS = 6  # Security headers for responses
```

You can get a dictionary of middleware positions using the `get_middleware_positions()` function:

```python
from fastblocks.middleware import get_middleware_positions

positions = get_middleware_positions()
print(positions)  # {'PROCESS_TIME': 0, 'CSRF': 1, ...}
```

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

#### Application Initialization Improvements (v0.13.2)

The FastBlocks application initialization process has been streamlined for better performance and reliability:

```python
from acb.adapters import import_adapter
from acb.depends import depends

# Get the application instance
App = import_adapter("app")
app = depends.get(App)

# The app is now pre-configured with:
# - Enhanced middleware stack management
# - Optimized dependency resolution
# - Improved error handling
# - Lazy loading for optional components
```

**Key Improvements:**

- **Faster Startup**: Lazy loading of non-critical components reduces initialization time
- **Better Error Handling**: Clear error messages for configuration issues and missing dependencies
- **Middleware Optimization**: Position-based middleware management with caching
- **Memory Efficiency**: Reduced memory footprint through optimized component loading

For more information about adapters, see the [Adapters Documentation](./fastblocks/adapters/README.md).

## Actions

Actions are utility functions that perform specific tasks:

- **Gather**: Discover and consolidate routes, templates, middleware, models, and application components
- **Sync**: Bidirectional synchronization of templates, settings, and cache across environments
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

The development server includes enhanced features:
- **Optimized Logging**: Uvicorn logging is integrated with ACB's InterceptHandler for cleaner output
- **Smart Reloading**: Excludes `tmp/*`, `settings/*`, and `templates/*` directories from reload monitoring for better performance
- **Template Development**: Templates are excluded from reload to prevent unnecessary restarts during template development

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
python -m fastblocks dev [--granian] [--host HOST] [--port PORT]
```

Running with hot-reloading enabled for development.

#### Run Command

```bash
python -m fastblocks run [--docker] [--granian] [--host HOST] [--port PORT]
```

Run in production mode.

#### Components Command

```bash
python -m fastblocks components
```

Show available FastBlocks components and their status.

## Migration Guide

### Updating from Version 0.13.1 to 0.13.2

Version 0.13.2 introduces simplified dependency management with direct ACB imports. While existing code will continue to work, we recommend updating to the new patterns for better performance and maintainability.

#### Import Pattern Changes

**Before (v0.13.1 and earlier):**
```python
# Old wrapper-based imports
from fastblocks.dependencies import Templates, App
from fastblocks.config import config
```

**After (v0.13.2+):**
```python
# Direct ACB imports (recommended)
from acb.adapters import import_adapter
from acb.depends import depends
from acb.config import Config

Templates = import_adapter("templates")
App = import_adapter("app")
config = depends.get(Config)
```

#### Route Handler Updates

**Before:**
```python
@depends.inject
async def homepage(request, templates=depends(Templates)):
    return await templates.render_template(request, "index.html")
```

**After:**
```python
@depends.inject
async def homepage(request, templates: Templates = depends()):
    return await templates.app.render_template(request, "index.html")
```

#### Benefits of the New Pattern

1. **Better Performance**: Direct ACB access eliminates wrapper overhead
2. **Improved Type Safety**: Explicit type annotations with adapters
3. **Enhanced Error Handling**: Built-in fallback mechanisms for missing dependencies
4. **Future Compatibility**: Aligned with ACB framework patterns

#### Template System Improvements

Version 0.13.2 includes enhanced null safety in template loaders:

- Automatic fallback when dependencies are unavailable
- Improved error messages for missing templates
- Better handling of cache and storage failures
- Enhanced dependency resolution order

#### CLI Enhancements

The CLI now includes:

- Optimized uvicorn logging configuration
- Template reload exclusions for better development experience
- Enhanced error reporting for configuration issues

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
- [**Running Tests**](./tests/TESTING.md): Comprehensive guide to testing FastBlocks components

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
