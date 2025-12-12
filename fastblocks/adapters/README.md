# FastBlocks Adapters

> **FastBlocks Documentation**: [Main](../../README.md) | [Core Features](../../README.md) | [Actions](../actions/README.md)

This directory contains the adapter system for FastBlocks, providing modular integration with external services and frameworks using protocol-based design and ACB 0.19.0+ compliance.

## Table of Contents

1. [Adapter Categories](#adapter-categories)
1. [Architecture](#architecture)
1. [Adapter Structure](#adapter-structure)
1. [Creating Custom Adapters](#creating-custom-adapters)
1. [MCP Server Foundation](#mcp-server-foundation)
1. [Health Monitoring](#health-monitoring)
1. [Best Practices](#best-practices)
1. [Integration Patterns](#integration-patterns)
1. [Troubleshooting](#troubleshooting)

## Adapter Categories

FastBlocks includes four main adapter categories, each providing specialized functionality:

### Images (`fastblocks/adapters/images/`)

Handle image processing, optimization, and delivery with cloud-based transformation:

- **Primary Modules**: Cloudinary (cloud transformation), ImageKit (real-time optimization + CDN)
- **Secondary Modules**: Cloudflare Images, TwicPics
- **Capabilities**: Upload, transformation, URL generation, responsive images
- **Fallback**: Standard HTML img tags

### Styles (`fastblocks/adapters/styles/`)

Manage CSS frameworks and custom styling systems:

- **Primary Modules**:
  - **Bulma**: Modern CSS framework based on Flexbox for responsive design
  - **Web Awesome**: Comprehensive icon library and UI components from Font Awesome
  - **Kelp**: Lightweight UI library for HTML-first development, powered by modern CSS and Web Components
  - **Vanilla**: Custom CSS with minimal framework overhead + semantic classes
- **Capabilities**: CSS framework integration, component styling, utility classes, responsive design

### Icons (`fastblocks/adapters/icons/`)

Provide icon libraries and rendering systems with SVG/font support:

- **Primary Modules**: FontAwesome, Lucide (SVG + font modes)
- **Secondary Modules**: Phosphor, Heroicons, Remix, Material Icons
- **Capabilities**: Icon library integration, SVG rendering, interactive icons

### Fonts (`fastblocks/adapters/fonts/`)

Manage web font loading and optimization:

- **Primary Modules**: Google Fonts (API integration)
- **Secondary Modules**: Font Squirrel (self-hosted)
- **Capabilities**: Font loading, family management, optimization, preloading

## Architecture

### Base Classes

Each adapter category has a base class implementing the `AdapterProtocol`:

```python
from fastblocks.adapters.images._base import ImagesBase, ImagesProtocol
from fastblocks.adapters.styles._base import StylesBase, StylesProtocol
from fastblocks.adapters.icons._base import IconsBase, IconsProtocol
from fastblocks.adapters.fonts._base import FontsBase, FontsProtocol
```

### ACB Integration

All adapters follow ACB 0.25.1+ patterns:

- **MODULE_ID**: Static UUID7 for adapter identification
- **MODULE_STATUS**: Adapter stability status (stable, beta, alpha, experimental)
- **Dependency Injection**: Modern `Inject[Type]` pattern with `@depends.inject` decorator
- **Settings Management**: YAML-based configuration with environment variable support

### Configuration

Adapter configuration is managed through YAML files in `settings/adapters/`:

```yaml
# settings/adapters/images.yml
images:
  adapter: cloudinary
  settings:
    cloud_name: my-cloud
    api_key: "${CLOUDINARY_API_KEY}"

# settings/adapters/styles.yml
styles:
  adapter: bulma
  settings:
    version: "0.9.4"
    cdn: true
```

### Template Integration

Adapters integrate with FastBlocks templates through custom Jinja2 filters:

```html
<!-- Image filters -->
[[ img_tag('product.jpg', 'Product Image', width=300) ]]

<!-- Style filters -->
<button class="[[ style_class('button') ]]">Click me</button>

<!-- Icon filters -->
<span>[[ icon_tag('home') | safe ]] Home</span>

<!-- Font imports -->
[% block head %]
    [[ font_import() ]]
[% endblock %]
```

## Adapter Structure

All adapters follow a consistent structure pattern:

```python
from contextlib import suppress
from uuid import UUID
from acb.config import AdapterBase, Settings
from acb.depends import depends


class MyAdapterSettings(Settings):
    """Adapter-specific settings."""

    api_key: str = ""
    cdn_url: str = ""
    default_quality: int = 80


class MyAdapter(AdapterBase):
    """My custom adapter implementation."""

    # Required ACB 0.25.1+ metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a1")  # Static UUID7
    MODULE_STATUS = "stable"  # stable, beta, alpha, experimental

    def __init__(self) -> None:
        """Initialize adapter."""
        super().__init__()
        self.settings = MyAdapterSettings()

        # Register with ACB dependency system
        with suppress(Exception):
            depends.set(self)
```

### Required Components

1. **Settings Class**: Inherits from `acb.config.Settings` with configuration options
1. **Adapter Class**: Inherits from `acb.config.AdapterBase` with protocol implementation
1. **MODULE_ID**: Static UUID7 for unique adapter identification
1. **MODULE_STATUS**: Current stability status (stable, beta, alpha, experimental)
1. **ACB Registration**: Self-registration in dependency system using `depends.set()`

## Creating Custom Adapters

Follow these steps to create a custom adapter that integrates with the FastBlocks ecosystem:

### Step 1: Define Settings

```python
from acb.config import Settings


class CustomImageSettings(Settings):
    """Settings for custom image adapter."""

    api_endpoint: str = "https://api.example.com"
    api_key: str = ""
    default_quality: int = 80
    supported_formats: list[str] = ["jpg", "png", "webp"]
```

### Step 2: Implement Protocol

```python
from typing import Any, Protocol


class CustomImageProtocol(Protocol):
    """Protocol for custom image operations."""

    async def upload_image(self, file_data: bytes, filename: str) -> str: ...
    async def get_image_url(self, image_id: str, **transformations: Any) -> str: ...
    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str: ...
```

### Step 3: Create Adapter

```python
from contextlib import suppress
from uuid import UUID
from acb.config import AdapterBase
from acb.depends import depends


class CustomImageAdapter(AdapterBase):
    """Custom image processing adapter."""

    # Required metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a5")
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize custom image adapter."""
        super().__init__()
        self.settings = CustomImageSettings()

        with suppress(Exception):
            depends.set(self)

    async def upload_image(self, file_data: bytes, filename: str) -> str:
        """Upload image to custom service."""
        # Implementation here
        pass

    async def get_image_url(self, image_id: str, **transformations: Any) -> str:
        """Generate optimized image URL."""
        # Implementation here
        pass

    def get_img_tag(self, image_id: str, alt: str, **attributes: Any) -> str:
        """Generate HTML img tag."""
        # Implementation here
        pass
```

### Step 4: Register with FastBlocks

Place your adapter in the appropriate category directory:

```
fastblocks/adapters/images/custom.py
```

The MCP discovery system will automatically detect and register your adapter.

## MCP Server Foundation

FastBlocks includes a Model Context Protocol (MCP) server foundation for adapter discovery and management. See [MCP Server Documentation](../mcp/README.md) for complete details.

### Key Components

1. **AdapterDiscoveryServer**: Discovers adapters from filesystem and ACB registry
1. **AdapterRegistry**: Central registry for adapter management
1. **HealthCheckSystem**: Monitors adapter health and validates functionality

### Using the MCP CLI

```bash
# List all available adapters
python -m fastblocks.mcp.cli list-adapters

# Show adapter categories
python -m fastblocks.mcp.cli list-categories

# Inspect specific adapter
python -m fastblocks.mcp.cli inspect cloudinary

# Validate adapter configuration
python -m fastblocks.mcp.cli validate bulma

# Check adapter health
python -m fastblocks.mcp.cli health --all
```

### Programmatic Usage

```python
from fastblocks.mcp import AdapterRegistry, HealthCheckSystem

# Initialize registry
registry = AdapterRegistry()
await registry.initialize()

# List available adapters
adapters = await registry.list_available_adapters()

# Get specific adapter
cloudinary = await registry.get_adapter("cloudinary")

# Health monitoring
health = HealthCheckSystem(registry)
health_result = await health.check_adapter_health("fontawesome")
```

## Health Monitoring

The health check system provides comprehensive adapter monitoring:

### Health Check Types

1. **Basic Validation**: Module structure and metadata verification
1. **Functional Checks**: Method availability and signature validation
1. **Integration Tests**: ACB registration and dependency resolution
1. **Performance Monitoring**: Response times and resource usage

### Health Status Levels

- **Healthy**: All checks pass successfully
- **Warning**: Minor issues or missing optional features
- **Error**: Critical failures preventing operation
- **Unknown**: Unable to determine status

### Monitoring Integration

```python
from fastblocks.mcp import HealthCheckSystem

health = HealthCheckSystem(registry)

# Schedule periodic monitoring
await health.schedule_periodic_checks(interval_minutes=30)

# Get system health summary
summary = health.get_system_health_summary()

# Configure custom health checks
health.configure_health_checks("my_adapter", {"timeout_seconds": 10, "retry_count": 3})
```

## Best Practices

### 1. Adapter Design

- **Single Responsibility**: Each adapter handles one specific integration
- **Protocol Compliance**: Implement all required protocol methods
- **Error Handling**: Graceful degradation with meaningful error messages
- **Configuration**: Use settings classes for all configurable options

### 2. Performance

- **Async by Default**: Use async/await for I/O operations
- **Caching**: Implement appropriate caching strategies
- **Resource Management**: Properly manage connections and resources
- **Lazy Loading**: Initialize resources only when needed

### 3. Security

- **API Key Management**: Never hardcode secrets, use environment variables
- **Input Validation**: Validate all inputs and parameters
- **Error Information**: Don't expose sensitive data in error messages
- **Secure Defaults**: Use secure settings by default

### 4. Testing

- **Unit Tests**: Test adapter logic in isolation
- **Integration Tests**: Test with real services using test credentials
- **Mock Services**: Provide mock implementations for testing
- **Health Checks**: Include comprehensive health validation

### 5. Documentation

- **Docstrings**: Document all public methods and classes
- **Type Hints**: Use complete type annotations
- **Examples**: Provide usage examples
- **Configuration**: Document all settings and options

## Integration Patterns

### 1. Template Integration

```python
# In Jinja2 templates
[[ image_url("hero-banner", width=800, height=400) ]]
[[ img_tag("profile-pic", "User Avatar", class="rounded") ]]

# In HTMY components
from fastblocks.adapters.images import get_image_adapter


class UserProfile:
    async def htmy(self, context):
        images = get_image_adapter()
        avatar_url = await images.get_image_url(self.avatar_id, width=100)
        return f'<img src="{avatar_url}" alt="Avatar">'
```

### 2. Dependency Injection

```python
from acb.depends import depends

# Get adapter instance
images = depends.get("images")
styles = depends.get("styles")


# Use in route handlers
@app.route("/upload")
async def upload_image(request):
    images = depends.get("images")
    file_data = await request.body()
    image_id = await images.upload_image(file_data, "upload.jpg")
    return {"image_id": image_id}
```

### 3. Multi-Adapter Support

```python
from fastblocks.mcp import AdapterRegistry

registry = AdapterRegistry()

# Register multiple image adapters
cloudinary = await registry.get_adapter("cloudinary")
imagekit = await registry.get_adapter("imagekit")

# Route to specific adapter based on requirements
if use_transformation_api:
    image_url = await cloudinary.get_image_url(image_id, **transforms)
else:
    image_url = await imagekit.get_image_url(image_id, **transforms)
```

## Troubleshooting

### Common Issues

**Import Errors**

- Ensure ACB is properly configured
- Check adapter base class inheritance
- Verify module path structure

**Registration Failures**

- Check MODULE_ID uniqueness (must be unique UUID7)
- Verify ACB dependency injection setup
- Ensure proper exception handling in `__init__`

**Health Check Failures**

- Validate adapter protocol implementation
- Check settings configuration in YAML files
- Verify external service connectivity

**Performance Issues**

- Review caching strategy
- Check async implementation (use async/await)
- Monitor resource usage

### Debug Commands

```bash
# Check adapter discovery
python -c "
from fastblocks.mcp import AdapterDiscoveryServer
import asyncio

async def debug():
    discovery = AdapterDiscoveryServer()
    adapters = await discovery.discover_adapters()
    for name, info in adapters.items():
        print(f'{name}: {info.module_status}')

asyncio.run(debug())
"

# Validate specific adapter
python -m fastblocks.mcp.cli validate my_adapter --format json

# Run comprehensive health check
python -m fastblocks.mcp.cli health --all --format json
```

### Logging and Monitoring

```python
import logging
from fastblocks.mcp import HealthCheckSystem

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("fastblocks.adapters")

# Monitor adapter health
health = HealthCheckSystem(registry)


async def monitor_adapters():
    results = await health.check_all_adapters()
    for name, result in results.items():
        if result.status == "error":
            logger.error(f"Adapter {name} failed: {result.message}")
        elif result.status == "warning":
            logger.warning(f"Adapter {name} warning: {result.message}")
```

## Development Status

This adapter system is part of the FastBlocks 8-week implementation plan:

- **Sprint 1** (Weeks 1-2): Foundation & Infrastructure ✓
- **Sprint 2** (Weeks 3-4): Primary Module Implementation
- **Sprint 3** (Weeks 5-6): Template Integration & Secondary Modules
- **Sprint 4** (Weeks 7-8): Quality Assurance & MCP Server Foundation

## Testing

Comprehensive test coverage using pytest with mock fixtures for each adapter category. See `tests/adapters/` for adapter-specific tests and `tests/conftest.py` for shared fixtures.

Coverage ratchet system maintains test coverage above the current baseline (31%).

## Usage

Adapters are automatically initialized based on configuration and accessed through ACB dependency injection:

```python
from acb.depends import depends

# Access adapters through dependency injection
images = depends.get("images")
styles = depends.get("styles")
icons = depends.get("icons")
fonts = depends.get("fonts")
```
