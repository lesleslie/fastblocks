# Minify Action

The Minify action provides code and asset optimization for FastBlocks web applications. It reduces file sizes through safe transformations, whitespace removal, and redundancy elimination while preserving functionality and improving performance.

## Table of Contents

- [Overview](#overview)
- [Features](#features)
- [Usage](#usage)
  - [HTML Minification](#html-minification)
  - [CSS Minification](#css-minification)
  - [JavaScript Minification](#javascript-minification)
- [API Reference](#api-reference)
- [Examples](#examples)
- [Performance Benefits](#performance-benefits)
- [Integration Patterns](#integration-patterns)
- [Best Practices](#best-practices)
- [Related Actions](#related-actions)

## Overview

The Minify action enables efficient code optimization for web applications by reducing file sizes without affecting functionality. It provides a consistent interface for minifying HTML, CSS, and JavaScript content using industry-standard optimization libraries.

## Features

- **HTML minification** with intelligent whitespace and comment removal
- **CSS optimization** with redundancy elimination and media query optimization
- **JavaScript compression** with safe transformations and formatting
- **Preserves functionality** while maximizing size reduction
- **Empty content handling** with graceful fallbacks
- **Fast processing** using optimized C-based libraries
- **Semantic interface** following FastBlocks action patterns

## Usage

Import the minify action from FastBlocks:

```python
from fastblocks.actions.minify import minify
```

### HTML Minification

Minify HTML content with automatic CSS and JavaScript optimization:

```python
# Basic HTML minification
html_content = """
<html>
<head>
    <title>My Page</title>
    <style>
        body { margin: 0; padding: 20px; }
        .container { max-width: 1200px; }
    </style>
</head>
<body>
    <div class="container">
        <h1>Welcome to FastBlocks</h1>
        <p>This is a sample page with embedded CSS and JavaScript.</p>
    </div>
    <script>
        function hello() {
            console.log('Hello, World!');
        }
    </script>
</body>
</html>
"""

minified_html = minify.html(html_content)
print(f"Original size: {len(html_content)} bytes")
print(f"Minified size: {len(minified_html)} bytes")
print(f"Reduction: {(1 - len(minified_html)/len(html_content))*100:.1f}%")
```

### CSS Minification

Optimize CSS with whitespace removal and media query optimization:

```python
# Basic CSS minification
css_content = """
/* Main styles */
body {
    margin: 0;
    padding: 0;
    font-family: Arial, sans-serif;
    background-color: #ffffff;
}

.container {
    max-width: 1200px;
    margin: 0 auto;
    padding: 20px;
}

@media (max-width: 768px) {
    .container {
        padding: 10px;
    }
}

/* Typography */
h1, h2, h3 {
    color: #333333;
    margin-bottom: 1rem;
}
"""

minified_css = minify.css(css_content)
print(f"Original CSS: {len(css_content)} bytes")
print(f"Minified CSS: {len(minified_css)} bytes")
print(f"Reduction: {(1 - len(minified_css)/len(css_content))*100:.1f}%")
```

### JavaScript Minification

Compress JavaScript while preserving functionality:

```python
# Basic JavaScript minification
js_content = """
// Application utilities
function calculateTotal(items) {
    let total = 0;
    for (let i = 0; i < items.length; i++) {
        total += items[i].price * items[i].quantity;
    }
    return total;
}

// Event handlers
document.addEventListener('DOMContentLoaded', function() {
    const button = document.getElementById('submit-btn');
    if (button) {
        button.addEventListener('click', function(event) {
            event.preventDefault();
            const items = getCartItems();
            const total = calculateTotal(items);
            displayTotal(total);
        });
    }
});

function displayTotal(amount) {
    const totalElement = document.getElementById('total');
    if (totalElement) {
        totalElement.textContent = '$' + amount.toFixed(2);
    }
}
"""

minified_js = minify.js(js_content)
print(f"Original JS: {len(js_content)} bytes")
print(f"Minified JS: {len(minified_js)} bytes")
print(f"Reduction: {(1 - len(minified_js)/len(js_content))*100:.1f}%")
```

## API Reference

### Core Methods

#### `minify.html()`

Minifies HTML content with embedded CSS and JavaScript optimization.

```python
@staticmethod
def html(html: str) -> str
```

**Parameters:**
- `html` (str): The HTML content to minify

**Returns:**
- `str`: The minified HTML content

**Features:**
- Removes unnecessary whitespace between tags
- Eliminates HTML comments
- Minifies embedded CSS (via `minify_css=True`)
- Minifies embedded JavaScript (via `minify_js=True`)
- Preserves necessary whitespace in `<pre>`, `<code>`, and other sensitive tags
- Handles empty or whitespace-only content gracefully

#### `minify.css()`

Optimizes CSS content by removing whitespace and redundancy.

```python
@staticmethod
def css(css: str) -> bytearray | bytes | str
```

**Parameters:**
- `css` (str): The CSS content to minify

**Returns:**
- `bytearray | bytes | str`: The minified CSS content

**Features:**
- Removes unnecessary whitespace and newlines
- Eliminates CSS comments
- Optimizes media queries (converts `@media (` to `@media(`)
- Preserves CSS functionality and specificity
- Handles empty or whitespace-only content gracefully

#### `minify.js()`

Compresses JavaScript code while preserving functionality.

```python
@staticmethod
def js(js: str) -> bytearray | bytes | str
```

**Parameters:**
- `js` (str): The JavaScript content to minify

**Returns:**
- `bytearray | bytes | str`: The minified JavaScript content

**Features:**
- Removes unnecessary whitespace and comments
- Preserves JavaScript semantics and functionality
- Adds strategic newlines after closing braces for readability
- Handles empty or whitespace-only content gracefully
- Safe transformations that don't break code execution

## Examples

### Template Integration

```python
from fastblocks.actions.minify import minify
from starlette.responses import HTMLResponse

async def render_page(request):
    """Render and minify a page template."""

    # Render template (assuming Jinja2 environment)
    html_content = await templates.render_async("page.html", {
        "title": "My FastBlocks App",
        "user": request.user,
        "data": await get_page_data()
    })

    # Minify the rendered HTML
    minified_html = minify.html(html_content)

    return HTMLResponse(
        content=minified_html,
        headers={
            "Content-Type": "text/html; charset=utf-8",
            "Content-Length": str(len(minified_html))
        }
    )
```

### Asset Pipeline

```python
from pathlib import Path
from fastblocks.actions.minify import minify

async def build_assets():
    """Build and minify static assets."""

    # Minify CSS files
    css_files = Path("static/css").glob("*.css")
    minified_css = []

    for css_file in css_files:
        content = css_file.read_text()
        minified = minify.css(content)

        # Save minified version
        output_file = Path("static/dist") / f"{css_file.stem}.min.css"
        output_file.write_text(minified)
        minified_css.append(output_file)

    # Minify JavaScript files
    js_files = Path("static/js").glob("*.js")
    minified_js = []

    for js_file in js_files:
        content = js_file.read_text()
        minified = minify.js(content)

        # Save minified version
        output_file = Path("static/dist") / f"{js_file.stem}.min.js"
        output_file.write_text(minified)
        minified_js.append(output_file)

    return {
        "css_files": minified_css,
        "js_files": minified_js
    }
```

### Middleware Integration

```python
from starlette.middleware.base import BaseHTTPMiddleware
from fastblocks.actions.minify import minify

class MinifyMiddleware(BaseHTTPMiddleware):
    """Middleware to automatically minify HTML responses."""

    def __init__(self, app, minify_html=True):
        super().__init__(app)
        self.minify_html = minify_html

    async def dispatch(self, request, call_next):
        response = await call_next(request)

        # Only minify HTML responses
        if (self.minify_html and
            response.headers.get("content-type", "").startswith("text/html")):

            # Get response body
            body = b""
            async for chunk in response.body_iterator:
                body += chunk

            # Minify HTML content
            html_content = body.decode("utf-8")
            minified_html = minify.html(html_content)

            # Update response
            response.body_iterator = [minified_html.encode("utf-8")]
            response.headers["content-length"] = str(len(minified_html))

        return response

# Usage in FastAPI app
app.add_middleware(MinifyMiddleware, minify_html=True)
```

### Batch Processing

```python
from fastblocks.actions.minify import minify
import asyncio
from pathlib import Path

async def minify_directory(input_dir: Path, output_dir: Path):
    """Minify all files in a directory."""

    results = {
        "html": [],
        "css": [],
        "js": [],
        "errors": []
    }

    # Ensure output directory exists
    output_dir.mkdir(parents=True, exist_ok=True)

    # Process all files
    for file_path in input_dir.rglob("*"):
        if not file_path.is_file():
            continue

        try:
            content = file_path.read_text(encoding="utf-8")
            relative_path = file_path.relative_to(input_dir)
            output_path = output_dir / relative_path

            # Ensure output subdirectory exists
            output_path.parent.mkdir(parents=True, exist_ok=True)

            if file_path.suffix == ".html":
                minified = minify.html(content)
                output_path.write_text(minified)
                results["html"].append(relative_path)

            elif file_path.suffix == ".css":
                minified = minify.css(content)
                output_path.write_text(minified)
                results["css"].append(relative_path)

            elif file_path.suffix == ".js":
                minified = minify.js(content)
                output_path.write_text(minified)
                results["js"].append(relative_path)

            # Calculate compression ratio
            original_size = len(content)
            minified_size = len(minified) if 'minified' in locals() else original_size
            ratio = (1 - minified_size / original_size) * 100 if original_size > 0 else 0

            print(f"Minified {relative_path}: {ratio:.1f}% reduction")

        except Exception as e:
            results["errors"].append(f"{relative_path}: {e}")

    return results

# Usage
results = await minify_directory(
    input_dir=Path("src/templates"),
    output_dir=Path("dist/templates")
)

print(f"Minified {len(results['html'])} HTML files")
print(f"Minified {len(results['css'])} CSS files")
print(f"Minified {len(results['js'])} JS files")
```

## Performance Benefits

### File Size Reduction

Typical compression ratios by content type:

- **HTML**: 15-30% reduction (varies by whitespace and comments)
- **CSS**: 20-40% reduction (depends on formatting and comments)
- **JavaScript**: 10-25% reduction (conservative minification preserves functionality)

### Network Performance

```python
# Example performance impact
original_sizes = {
    "main.css": 45_000,      # 45KB
    "app.js": 120_000,       # 120KB
    "index.html": 25_000     # 25KB
}

minified_sizes = {
    "main.css": 32_000,      # 32KB (29% reduction)
    "app.js": 95_000,        # 95KB (21% reduction)
    "index.html": 20_000     # 20KB (20% reduction)
}

total_original = sum(original_sizes.values())  # 190KB
total_minified = sum(minified_sizes.values())  # 147KB
total_savings = total_original - total_minified  # 43KB (23% reduction)

# At 1Mbps connection: ~0.34 seconds saved per page load
# At 100 concurrent users: ~34 seconds total bandwidth saved
```

### Browser Benefits

- **Faster parsing**: Less content to parse and process
- **Reduced memory usage**: Smaller DOM trees and style sheets
- **Improved caching**: More efficient cache utilization
- **Better mobile performance**: Critical for limited bandwidth connections

## Integration Patterns

### Build Pipeline Integration

```python
# Build script integration
from fastblocks.actions.minify import minify
from fastblocks.actions.gather import gather

async def build_production_assets():
    """Complete build pipeline with gathering and minification."""

    # Gather templates
    templates = await gather.templates()

    # Process each template
    for template_path in templates.template_paths:
        if template_path.suffix in [".html", ".htm"]:
            content = await template_path.read_text()
            minified = minify.html(content)

            # Save to production directory
            prod_path = Path("dist/templates") / template_path.name
            await prod_path.write_text(minified)

    # Gather and minify static assets
    static_files = Path("static").rglob("*")
    for static_file in static_files:
        if static_file.suffix == ".css":
            content = static_file.read_text()
            minified = minify.css(content)
            prod_path = Path("dist/static") / static_file.relative_to("static")
            prod_path.parent.mkdir(parents=True, exist_ok=True)
            prod_path.write_text(minified)

        elif static_file.suffix == ".js":
            content = static_file.read_text()
            minified = minify.js(content)
            prod_path = Path("dist/static") / static_file.relative_to("static")
            prod_path.parent.mkdir(parents=True, exist_ok=True)
            prod_path.write_text(minified)
```

### Development vs Production

```python
from fastblocks.actions.minify import minify

class TemplateRenderer:
    def __init__(self, minify_in_production=True):
        self.minify_in_production = minify_in_production

    async def render(self, template_name: str, context: dict) -> str:
        # Render template
        html = await self.template_env.get_template(template_name).render_async(context)

        # Minify in production only
        if self.minify_in_production and self.is_production():
            html = minify.html(html)

        return html

    def is_production(self) -> bool:
        import os
        return os.getenv("ENVIRONMENT") == "production"
```

## Best Practices

### 1. Environment-Specific Minification

```python
# Only minify in production to preserve debugging
minify_enabled = os.getenv("ENVIRONMENT") == "production"
if minify_enabled:
    content = minify.html(content)
```

### 2. Error Handling

```python
def safe_minify_html(html_content: str) -> str:
    """Safely minify HTML with fallback."""
    try:
        return minify.html(html_content)
    except Exception as e:
        logger.warning(f"HTML minification failed: {e}")
        return html_content  # Return original on error
```

### 3. Content Validation

```python
def validate_before_minify(content: str, content_type: str) -> bool:
    """Validate content before minification."""
    if not content or content.isspace():
        return False

    if content_type == "html" and "<html" not in content.lower():
        return False  # Probably a fragment, skip minification

    return True
```

### 4. Performance Monitoring

```python
import time
from fastblocks.actions.minify import minify

def minify_with_metrics(content: str, content_type: str) -> tuple[str, dict]:
    """Minify content and return performance metrics."""
    start_time = time.time()
    original_size = len(content)

    if content_type == "html":
        minified = minify.html(content)
    elif content_type == "css":
        minified = minify.css(content)
    elif content_type == "js":
        minified = minify.js(content)
    else:
        return content, {}

    end_time = time.time()
    minified_size = len(minified)

    metrics = {
        "original_size": original_size,
        "minified_size": minified_size,
        "compression_ratio": (1 - minified_size / original_size) * 100,
        "processing_time": end_time - start_time
    }

    return minified, metrics
```

### 5. Cache Integration

```python
from fastblocks.actions.minify import minify

class CachedMinifier:
    def __init__(self):
        self.cache = {}

    def minify_html(self, content: str) -> str:
        # Use content hash as cache key
        import hashlib
        content_hash = hashlib.blake2b(content.encode()).hexdigest()

        if content_hash in self.cache:
            return self.cache[content_hash]

        minified = minify.html(content)
        self.cache[content_hash] = minified
        return minified
```

## Related Actions

- [Gather Action](../gather/README.md): Discover templates and assets before minifying
- [Sync Action](../sync/README.md): Synchronize minified assets across environments
- [ACB Compress Action](https://github.com/fastblocks/acb/tree/main/acb/actions/compress): Additional compression utilities
