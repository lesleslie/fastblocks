# FastBlocks Adapters

> **FastBlocks Documentation**: [Main](../../README.md) | [Core Features](../README.md) | [Actions](../actions/README.md) | [Adapters](./README.md)

Adapters in FastBlocks provide standardized interfaces to external systems and services. Each adapter category includes a base class that defines the interface and multiple implementations. This architecture not only promotes code organization but also enables powerful capabilities like cloud provider flexibility, simplified migrations, and hybrid deployment strategies.

## Relationship with ACB

FastBlocks adapters extend [ACB's adapter pattern](https://github.com/lesleslie/acb/blob/main/acb/adapters/README.md) with web-specific functionality:

- **ACB Adapter Foundation**: Provides the core adapter pattern, configuration loading, and dependency injection
- **FastBlocks Adapter Extensions**: Adds web-specific adapters like templates, routes, auth, and admin interfaces

While ACB provides general-purpose adapters (cache, storage, database), FastBlocks focuses on adapters needed for web applications. This allows you to use the same adapter pattern for both infrastructure and web components.

## Available Adapters

| Adapter | Description | Implementations |
|---------|-------------|----------------|
| [App](#app-adapter) | Application configuration | `default` |
| [Auth](#auth-adapter) | Authentication providers | `basic` |
| [Admin](#admin-adapter) | Admin interface | `sqladmin` |
| [Routes](#routes-adapter) | Route management | `default` |
| [Templates](#templates-adapter) | Template engine | `jinja2` |
| [Sitemap](#sitemap-adapter) | Sitemap generation | `asgi` |

## Adapter System

FastBlocks uses a pluggable adapter system that allows you to:

1. **Swap implementations**: Change the implementation without changing your code
2. **Configure via settings**: Select adapters through configuration
3. **Extend with custom adapters**: Create your own adapters for specific needs
4. **Enable multi-cloud strategies**: Swap storage, cache or auth adapters to work with different cloud providers
5. **Create hybrid deployments**: Mix on-premise and cloud services by using different adapter implementations
6. **Simplify migrations**: Move between infrastructure providers by changing adapters rather than rewriting application logic

### Using Adapters

Adapters are typically accessed through dependency injection:

```python
from acb.depends import depends
from acb.adapters import import_adapter

# Import the adapter (automatically uses the one enabled in config)
Templates = import_adapter("templates")

# Get the adapter instance via dependency injection
templates = depends.get(Templates)

# Use the adapter with a consistent API regardless of implementation
await templates.app.render_template(request, "index.html")
```

### Adapter Configuration

Adapters are configured in your settings files:

```yaml
# settings/adapters.yml
app: default
auth: basic
admin: sqladmin
templates: jinja2
```

## App Adapter

The App adapter manages application configuration and initialization.

```python
from acb.depends import depends
from acb.adapters import import_adapter

App = import_adapter("app")
app = depends.get(App)

# Access app settings
app_name = app.settings.name
app_style = app.settings.style
```

For more details, see the [App Adapter Documentation](./app/README.md).

## Auth Adapter

The Auth adapter provides authentication mechanisms for your application.

```python
from acb.depends import depends
from acb.adapters import import_adapter

Auth = import_adapter("auth")
auth = depends.get(Auth)

# Authenticate a user
user = await auth.authenticate(username, password)
```

For more details, see the [Auth Adapter Documentation](./auth/README.md).

## Admin Adapter

The Admin adapter provides an administrative interface for your application.

```python
from acb.depends import depends
from acb.adapters import import_adapter

Admin = import_adapter("admin")
admin = depends.get(Admin)

# Register a model with the admin interface
admin.register_model(User)
```

For more details, see the [Admin Adapter Documentation](./admin/README.md).

## Routes Adapter

The Routes adapter manages route discovery and registration.

```python
from acb.depends import depends
from acb.adapters import import_adapter

Routes = import_adapter("routes")
routes = depends.get(Routes)

# Access the routes
app_routes = routes.routes
```

For more details, see the [Routes Adapter Documentation](./routes/README.md).

## Templates Adapter

The Templates adapter provides template rendering capabilities.

```python
from acb.depends import depends
from acb.adapters import import_adapter

Templates = import_adapter("templates")
templates = depends.get(Templates)

# Render a template
response = await templates.app.render_template(request, "index.html")
```

For more details, see the [Templates Adapter Documentation](./templates/README.md).

## Sitemap Adapter

The Sitemap adapter generates sitemaps for your application.

```python
from acb.depends import depends
from acb.adapters import import_adapter

Sitemap = import_adapter("sitemap")
sitemap = depends.get(Sitemap)

# Generate a sitemap
sitemap_content = await sitemap.generate()
```

For more details, see the [Sitemap Adapter Documentation](./sitemap/README.md).

## Creating Custom Adapters

You can create your own adapters by following these steps:

1. Create a directory for your adapter in the `adapters` directory
2. Create a `_base.py` file with the base class and settings
3. Create implementation files for each specific implementation
4. Register your adapter with the dependency injection system

### Example: Creating a Payment Adapter

```python
# fastblocks/adapters/payment/_base.py
from acb.config import Settings, AdapterBase

class PaymentBaseSettings(Settings):
    currency: str = "USD"
    default_timeout: int = 30

class PaymentBase(AdapterBase):
    async def charge(self, amount: float, description: str) -> str:
        """Charge a payment and return a transaction ID"""
        raise NotImplementedError()

    async def refund(self, transaction_id: str) -> bool:
        """Refund a previous transaction"""
        raise NotImplementedError()
```

```python
# fastblocks/adapters/payment/stripe.py
from ._base import PaymentBase, PaymentBaseSettings
from pydantic import SecretStr
import stripe

class StripeSettings(PaymentBaseSettings):
    api_key: SecretStr = SecretStr("sk_test_default")

class Stripe(PaymentBase):
    settings: StripeSettings | None = None

    async def init(self) -> None:
        if self.settings is not None:
            stripe.api_key = self.settings.api_key.get_secret_value()

    async def charge(self, amount: float, description: str) -> str:
        response = await stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=self.settings.currency if self.settings else "USD",
            description=description
        )
        return response.id
```

```python
# fastblocks/adapters/payment/__init__.py
from acb.depends import depends
from ._base import PaymentBase
from .stripe import Stripe

depends.set(Stripe)
```

Then you can use your custom adapter:

```python
from acb.depends import depends
from acb.adapters import import_adapter

Payment = import_adapter("payment")
payment = depends.get(Payment)

# Use the adapter
transaction_id = await payment.charge(19.99, "Product purchase")
```

## Cloud Provider Flexibility

One of FastBlocks' most powerful features is the ability to switch between different cloud providers or create hybrid deployments by simply swapping adapter implementations.

### Multi-Cloud Strategies

By using adapters for infrastructure concerns, you can easily:

- **Prevent vendor lock-in**: Abstract cloud-specific APIs behind adapter interfaces
- **Optimize for cost**: Switch between providers based on pricing changes
- **Geographic distribution**: Use different providers in different regions
- **Risk mitigation**: Maintain backup deployments on alternative clouds
- **Compliance requirements**: Support multiple clouds to meet regulatory needs

### Example: Storage Adapters

You could implement storage adapters for different providers:

```python
# Local filesystem storage
class LocalStorage(StorageBase):
    async def write(self, path, data):
        # Write to local filesystem

# AWS S3 storage
class S3Storage(StorageBase):
    async def write(self, path, data):
        # Write to S3 bucket

# Azure Blob storage
class AzureBlobStorage(StorageBase):
    async def write(self, path, data):
        # Write to Azure Blob Storage
```

Then switch between them with a simple configuration change:

```yaml
# settings/adapters.yml for development
storage: local

# settings/adapters.yml for production on AWS
storage: s3

# settings/adapters.yml for production on Azure
storage: azure
```

### Hybrid Deployment Strategies

You can also mix and match adapters to create hybrid deployments:

```yaml
# Use local file storage but Redis caching
storage: local
cache: redis

# Use AWS S3 for storage but Azure AD for authentication
storage: s3
auth: azure_ad
```

This architecture makes FastBlocks particularly well-suited for organizations that need infrastructure flexibility or operate in multi-cloud environments.
