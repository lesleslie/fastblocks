# FastBlocks Adapters

> **FastBlocks Documentation**: [Main](../../README.md) | [Core Features](../README.md) | [Actions](../actions/README.md) | [Adapters](./README.md)

Adapters in FastBlocks provide standardized interfaces to external systems and services. Each adapter category includes a base class that defines the interface and multiple implementations.

## Available Adapters

| Adapter | Description | Implementations |
|---------|-------------|----------------|
| [App](#app-adapter) | Application configuration | Default |
| [Auth](#auth-adapter) | Authentication providers | Basic |
| [Admin](#admin-adapter) | Admin interface | SQLAdmin |
| [Routes](#routes-adapter) | Route management | Default |
| [Templates](#templates-adapter) | Template engine | Jinja2 |
| [Sitemap](#sitemap-adapter) | Sitemap generation | Default |

## Adapter System

FastBlocks uses a pluggable adapter system that allows you to:

1. **Swap implementations**: Change the implementation without changing your code
2. **Configure via settings**: Select adapters through configuration
3. **Extend with custom adapters**: Create your own adapters for specific needs

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
from acb.config import AdapterBase, Settings

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
    settings: StripeSettings = None

    async def init(self) -> None:
        stripe.api_key = self.settings.api_key.get_secret_value()

    async def charge(self, amount: float, description: str) -> str:
        response = await stripe.PaymentIntent.create(
            amount=int(amount * 100),  # Convert to cents
            currency=self.settings.currency,
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
