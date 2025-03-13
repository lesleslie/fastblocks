# Admin Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Admin adapter provides an administrative interface for FastBlocks applications.

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
    id: Optional[int] = Field(default=None, primary_key=True)
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

    # Add custom actions
    def is_accessible(self):
        return True  # Add your access control logic here

    def is_visible(self):
        return True

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

## Implementation Details

The Admin adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `sqladmin.py`: Provides the SQLAlchemy Admin implementation

### Base Class

```python
from acb.config import AdapterBase, Settings
from typing import Any, Type

class AdminBaseSettings(Settings):
    enabled: bool = True
    title: str = "FastBlocks Admin"
    logo_url: Optional[str] = None
    style: str = "default"

class AdminBase(AdapterBase):
    def register_model(self, model: Type[Any]) -> None:
        """Register a model with the admin interface"""
        raise NotImplementedError()
```

## SQLAdmin Implementation

The `sqladmin` implementation uses the [SQLAdmin](https://aminalaee.dev/sqladmin/) package to provide a powerful admin interface for SQLAlchemy models.

### Features

- **CRUD Operations**: Create, read, update, and delete records
- **Filtering and Sorting**: Filter and sort records by various fields
- **Search**: Search across multiple fields
- **Pagination**: Navigate through large datasets
- **Form Validation**: Automatic form validation based on model constraints
- **Authentication**: Secure the admin interface with authentication
- **Customization**: Customize the appearance and behavior of the admin interface

## Customization

You can create a custom admin adapter for more specialized admin interfaces:

```python
# myapp/adapters/admin/custom.py
from fastblocks.adapters.admin._base import AdminBase, AdminBaseSettings

class CustomAdminSettings(AdminBaseSettings):
    dashboard_template: str = "admin/dashboard.html"

class CustomAdmin(AdminBase):
    settings: CustomAdminSettings = None

    async def init(self) -> None:
        # Initialize custom admin interface
        pass

    def register_model(self, model: Type[Any]) -> None:
        # Register model with custom admin interface
        pass
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
admin: custom
```
