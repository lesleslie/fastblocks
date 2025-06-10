# Admin Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Admin adapter provides an administrative interface for FastBlocks applications.

## Relationship with ACB

The Admin adapter is a FastBlocks-specific extension that builds on ACB's adapter pattern:

- **ACB Foundation**: Provides the adapter pattern, configuration loading, and dependency injection
- **FastBlocks Extension**: Implements admin interface integration with SQLAlchemy

The Admin adapter integrates with ACB's SQL adapter for database access and leverages ACB's dependency injection system to connect with other components like Templates and Models.

## Overview

The Admin adapter allows you to:

- Create an admin dashboard for your application
- Manage database models through a web interface
- Customize the admin interface appearance and behavior

## Available Implementations

| Implementation | Description |
|----------------|-------------|
| `sqladmin` | SQLAlchemy Admin interface |

## Configuration

Configure the Admin adapter in your settings:

```yaml
# settings/admin.yml
admin:
  enabled: true
  title: "My Application Admin"
  logo_url: "/static/logo.png"
  style: "default"
```

## Usage

### Basic Setup

```python
from acb.depends import depends
from acb.adapters import import_adapter
from fastblocks.applications import FastBlocks
from sqlmodel import SQLModel, Field

# Define your models
class User(SQLModel, table=True):
    id: int | None = Field(default=None, primary_key=True)
    username: str
    email: str
    is_active: bool = True

# Create your application
app = FastBlocks()

# Get the admin adapter
Admin = import_adapter("admin")
admin = depends.get(Admin)

# Register your models with the admin interface
admin.register_model(User)
```

### Customizing Model Views

You can customize how models appear in the admin interface:

```python
from sqladmin import ModelView

class UserAdmin(ModelView, model=User):
    column_list = [User.id, User.username, User.email, User.is_active]
    column_searchable_list = [User.username, User.email]
    column_sortable_list = [User.id, User.username]
    column_default_sort = [(User.id, True)]

    # Customize forms
    form_columns = [User.username, User.email, User.is_active]

    # Customize display names and formatting
    column_labels = {
        User.email: "Email Address",
        User.is_active: "Account Status"
    }

    # Format display values
    column_formatters = {
        User.is_active: lambda m, a: "Active" if m.is_active else "Inactive"
    }

    # Add validators
    form_args = {
        "username": {
            "validators": [DataRequired(), Length(min=3, max=20)]
        },
        "email": {
            "validators": [DataRequired(), Email()]
        }
    }

    # Control access permissions
    def is_accessible(self):
        # Example: Check if user is authenticated and has admin role
        from flask_login import current_user
        return current_user.is_authenticated and current_user.has_role("admin")

    def is_visible(self):
        return True

    # Add custom actions
    @action(
        name="activate_users",
        label="Activate selected users",
        confirmation="Are you sure you want to activate selected users?"
    )
    def action_activate_users(self, ids):
        """Custom action to bulk activate users"""
        for model in self.session.query(self.model).filter(self.model.id.in_(ids)).all():
            model.is_active = True
        self.session.commit()
        return len(ids)

# Register the custom model view
admin.register_model(UserAdmin)
```

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `enabled` | `bool` | `True` | Whether the admin interface is enabled |
| `title` | `str` | `"FastBlocks Admin"` | The title of the admin interface |
| `logo_url` | `Optional[str]` | `None` | URL to the logo image |
| `style` | `str` | `"default"` | The style/theme of the admin interface |
| `base_url` | `str` | `"/admin"` | URL prefix for the admin interface |
| `secure_environments` | `List[str]` | `["production"]` | Environments where security measures are enforced |
| `allowed_ips` | `Optional[List[str]]` | `None` | List of IPs/CIDR blocks allowed to access admin when secure |
| `template_overrides` | `Optional[Dict[str, str]]` | `None` | Map of template names to override paths |
| `custom_scripts` | `List[str]` | `[]` | List of custom JS files to include |
| `custom_styles` | `List[str]` | `[]` | List of custom CSS files to include |
| `menu_items` | `List[Dict]` | `[]` | Additional navigation menu items |
| `default_sort_dir` | `str` | `"desc"` | Default sort direction (asc/desc) |
| `page_size` | `int` | `25` | Number of items per page in lists |

## Theme Customization

The admin interface supports two built-in themes:

1. **Bootstrap Theme** (default): Clean, responsive design based on Bootstrap 5
2. **Material Theme**: Material Design-inspired theme with cards and elevated components

### Changing the Theme

```yaml
# settings/admin.yml
admin:
  style: "material"  # or "bootstrap" (default)
```

### Custom Styling

You can add your own CSS to customize the admin interface:

```yaml
# settings/admin.yml
admin:
  custom_styles:
    - "/static/admin/custom.css"
```

Then create your CSS file:

```css
/* static/admin/custom.css */
.admin-header {
  background-color: #1a237e;
  color: white;
}

.admin-sidebar {
  background-color: #f5f5f5;
}

/* Override SQLAdmin components */
.admin-card {
  border-radius: 8px;
  box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
}
```

### Template Overrides

You can override specific admin templates:

```yaml
# settings/admin.yml
admin:
  template_overrides:
    "layout.html": "my_admin/layout.html"
    "list.html": "my_admin/list.html"
```

Then create your templates in your app's templates directory.

## Implementation Details

The Admin adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `sqladmin.py`: Provides the SQLAlchemy Admin implementation

### Base Class

```python
from acb.config import Settings

class AdminBaseSettings(Settings):
    enabled: bool = True
    title: str = "FastBlocks Admin"
    logo_url: str | None = None
    style: str = "default"

class AdminBase(AdapterBase):
    def register_model(self, model: type[object]) -> None:
        """Register a model with the admin interface"""
        raise NotImplementedError()
```

## SQLAdmin Implementation

The `sqladmin` implementation uses the [SQLAdmin](https://github.com/aminalaee/sqladmin) package to provide a powerful admin interface for SQLAlchemy models.

### Features

- **CRUD Operations**: Create, read, update, and delete records
- **Filtering and Sorting**: Filter and sort records by various fields
- **Search**: Search across multiple fields
- **Pagination**: Navigate through large datasets
- **Form Validation**: Automatic form validation based on model constraints
- **Authentication**: Secure the admin interface with authentication
- **Customization**: Customize the appearance and behavior of the admin interface
- **File Uploads**: Support for file uploads with preview
- **Rich Text Editing**: Integrated WYSIWYG editors for content fields
- **Export**: Export data to various formats (CSV, JSON)

### Advanced Usage Examples

#### Custom Form Fields

```python
from sqladmin import ModelView
from wtforms.fields import StringField, TextAreaField
from wtforms.widgets import ColorInput, FileInput

class ProductAdmin(ModelView, model=Product):
    column_list = [Product.id, Product.name, Product.price, Product.color, Product.is_available]

    # Custom form fields
    form_overrides = {
        "description": TextAreaField,
        "color": StringField,
    }

    form_widget_args = {
        "color": {"widget": ColorInput()},
        "image": {"widget": FileInput()}
    }

    # Custom formatters for display
    column_formatters = {
        Product.price: lambda m, a: f"${m.price:.2f}",
        Product.image: lambda m, a: Markup(f"<img src='{m.image}' width='100'>")
    }
```

#### Relationship Handling

```python
class OrderAdmin(ModelView, model=Order):
    column_list = [Order.id, Order.customer, Order.date, Order.total]

    # Handle relationships
    form_ajax_refs = {
        "customer": {
            "fields": (Customer.name, Customer.email),
            "order_by": (Customer.name,),
            "page_size": 10
        },
        "products": {
            "fields": (Product.name,),
            "order_by": (Product.name,),
            "page_size": 10
        }
    }

    # Inline editing for order items
    inline_models = [(
        OrderItem,
        {
            "column_labels": {"quantity": "Qty"},
            "form_columns": ["product", "quantity", "price"],
            "form_args": {"price": {"default": 0.0}}
        }
    )]
```

#### Custom Admin Actions

```python
from sqladmin import action

class UserAdmin(ModelView, model=User):
    # Standard configuration...

    @action(
        name="send_welcome_email",
        label="Send Welcome Email",
        confirmation="Send welcome email to selected users?"
    )
    def send_welcome_email(self, ids):
        users = self.session.query(self.model).filter(self.model.id.in_(ids)).all()
        for user in users:
            email_service.send_welcome(user.email, user.name)
        flash(f"Welcome emails sent to {len(users)} users")
        return len(users)

    @action(
        name="export_user_data",
        label="Export User Data",
        confirmation="Export data for selected users?"
    )
    def export_user_data(self, ids):
        # Logic to export user data to CSV
        users = self.session.query(self.model).filter(self.model.id.in_(ids)).all()
        return export_to_csv(users, ["id", "username", "email", "created_at"])
```

## Securing the Admin Interface

It's crucial to protect your admin interface from unauthorized access. Here are several approaches:

### Using Authentication Middleware

```python
from starlette.middleware.authentication import AuthenticationMiddleware
from starlette.authentication import AuthCredentials, BaseUser

class AdminAuthBackend:
    async def authenticate(self, request):
        # Your authentication logic here
        if not is_authorized_admin(request):
            return None
        return AuthCredentials(["admin"]), AdminUser(request)

# In your application startup
app.add_middleware(AuthenticationMiddleware, backend=AdminAuthBackend())
```

### Using Environment-Based Security

```python
# settings/admin.yml
admin:
  enabled: true
  secure_environments: ["production", "staging"]
  allowed_ips: ["10.0.0.0/8", "127.0.0.1"]
```

```python
# In your admin adapter init
if self.settings.secure_environments and app_env in self.settings.secure_environments:
    # Apply IP restrictions
    app.add_middleware(IPRestrictionMiddleware,
                       allowed_ips=self.settings.allowed_ips)
```

### Using FastBlocks Auth Adapter Integration

```python
# In your FastBlocks app setup
app = FastBlocks()

# Get auth and admin adapters
Auth = import_adapter("auth")
Admin = import_adapter("admin")

auth = depends.get(Auth)
admin = depends.get(Admin)

# Link authentication to admin
admin.set_auth_handler(auth.authenticate_admin)
```

## Custom Admin Dashboards

You can create a custom dashboard for your admin interface:

```python
from fastblocks.adapters.admin import AdminBase, AdminBaseSettings
from sqladmin import Admin, ModelView
from starlette.requests import Request
from starlette.responses import Response

class CustomAdminSettings(AdminBaseSettings):
    dashboard_template: str = "admin/dashboard.html"
    custom_scripts: list[str] = ["admin/charts.js"]
    custom_styles: list[str] = ["admin/dashboard.css"]

class CustomAdmin(AdminBase):
    settings: CustomAdminSettings | None = None

    async def init(self) -> None:
        # Initialize SQLAdmin
        self.admin = Admin(
            self.app,
            self.engine,
            title=self.settings.title,
            base_url="/admin",
            authentication_backend=self.auth_backend,
            templates_dir="templates/admin"
        )

        # Register custom dashboard route
        @self.admin.add_view
        class DashboardView:
            name = "Dashboard"
            icon = "fa fa-home"

            def is_visible(self):
                return True

            def is_accessible(self):
                return True

            @admin.expose("/")
            def index(self, request: Request) -> Response:
                stats = {
                    "users": self.get_user_stats(),
                    "content": self.get_content_stats(),
                    "system": self.get_system_stats()
                }
                return self.render_template(
                    "admin/dashboard.html",
                    request=request,
                    stats=stats
                )

            def get_user_stats(self):
                # Query database for user statistics
                return {"total": 1250, "active": 860, "new_today": 15}

    def register_model(self, model: type[object]) -> None:
        if hasattr(self, "admin"):
            self.admin.add_view(model)
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
admin: custom
```
