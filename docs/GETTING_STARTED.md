# Getting Started with FastBlocks

> **FastBlocks Documentation**: [Main](../README.md) | [Core Features](../README.md#fastblocks) | [Actions](../fastblocks/actions/README.md) | [Adapters](../fastblocks/adapters/README.md)
>
> _Last reviewed: 2025-11-19_

This guide consolidates the Quick Start walkthrough and the Common Patterns examples that previously lived in `README.md`. Use it to bootstrap a project, explore HTMX block rendering, and learn the modern `Inject[Type]` dependency injection style.

## Quick Start

Let's build a simple FastBlocks application step by step:

### 1. Create Your Application File

Create a file named `myapp.py` with the following code:

```python
from starlette.routing import Route
from acb.adapters import import_adapter
from acb.depends import Inject, depends

# Import adapters - these are pluggable components that FastBlocks uses
# The Templates adapter handles rendering Jinja2 templates
# The App adapter provides the FastBlocks application instance
Templates = import_adapter("templates")  # Get the configured template adapter
App = import_adapter("app")  # Get the configured app adapter


# Define a route handler for the homepage
# Modern ACB 0.25.1+ uses @depends.inject decorator with Inject[Type] type hints
@depends.inject
async def homepage(request, templates: Inject[Templates]):
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
async def counter_block(request, templates: Inject[Templates]):
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
# For module-level dependency injection, use depends.get()
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
from acb.depends import Inject, depends

Templates = import_adapter("templates")


@depends.inject
async def user_profile_block(request, templates: Inject[Templates]):
    user_id = request.path_params["user_id"]

    # Fetch user data (in a real app, this would come from a database)
    user = {
        "id": user_id,
        "name": f"User {user_id}",
        "email": f"user{user_id}@example.com",
    }

    # Render just the user profile block
    return await templates.app.render_template_block(
        request,
        "users/profile.html",  # Template file
        "profile_block",  # Block name within the template
        context={"user": user},
    )


routes = [Route("/users/{user_id}/profile", endpoint=user_profile_block)]
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
from acb.depends import Inject, depends

Templates = import_adapter("templates")


@depends.inject
async def contact_form(request, templates: Inject[Templates]):
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
            request, "contact/form.html", "success_block", context={"name": name}
        )

    # For GET requests, render the form
    return await templates.app.render_template(request, "contact/form.html", context={})


routes = [Route("/contact", endpoint=contact_form, methods=["GET", "POST"])]
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
from acb.depends import Inject, depends
from acb.config import Config

# Import adapters using the modern ACB 0.25.1+ pattern
Templates = import_adapter("templates")
Cache = import_adapter("cache")


@depends.inject
async def dashboard(
    request,
    templates: Inject[Templates],
    cache: Inject[Cache],
    config: Inject[Config],
):
    # Get cached data or compute it
    cache_key = "dashboard_stats"
    stats = await cache.get(cache_key)

    if not stats:
        # In a real app, you would fetch this from a database
        stats = {"users": 1250, "posts": 5432, "comments": 15876}

        # Cache the stats for 5 minutes
        await cache.set(cache_key, stats, ttl=300)

    # Get app name from configuration
    app_name = config.app.name

    return await templates.app.render_template(
        request, "dashboard.html", context={"app_name": app_name, "stats": stats}
    )


routes = [Route("/dashboard", endpoint=dashboard)]
```

This example demonstrates the modern ACB 0.25.1+ `Inject[Type]` pattern for type-safe dependency injection with automatic fallbacks.

## Next Steps

1. Explore the [Template Adapter guide](../fastblocks/adapters/templates/README.md) for filters, loaders, and async internals.
1. Deep-dive into [async template rendering](./JINJA2_ASYNC_ENVIRONMENT_USAGE.md) if you hit inheritance or streaming issues.
1. Review the [Template Examples](./examples/TEMPLATE_EXAMPLES.md) for fragment ideas.
1. When you're ready to customize infrastructure, browse the [Adapters reference](../fastblocks/adapters/README.md).
