# Auth Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Auth adapter provides authentication mechanisms for FastBlocks applications.

## Overview

The Auth adapter allows you to:

- Authenticate users with various methods
- Protect routes with authentication requirements
- Manage user sessions

## Available Implementations

| Implementation | Description |
|----------------|-------------|
| `basic` | Basic username/password authentication |

## Configuration

Configure the Auth adapter in your settings:

```yaml
# settings/auth.yml
auth:
  token_id: "myapp"
  token_lifetime: 86400  # 24 hours in seconds
```

## Usage

### Basic Authentication

```python
from acb.depends import depends
from acb.adapters import import_adapter
from starlette.routing import Route
from starlette.responses import RedirectResponse

Auth = import_adapter("auth")
auth = depends.get(Auth)

async def login(request):
    if request.method == "POST":
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        user = await auth.authenticate(username, password)
        if user:
            # Set session data
            request.session["user"] = user.dict()
            return RedirectResponse("/dashboard", status_code=303)

        # Authentication failed
        return await templates.app.render_template(
            request, "login.html", context={"error": "Invalid credentials"}
        )

    return await templates.app.render_template(request, "login.html")

async def logout(request):
    request.session.clear()
    return RedirectResponse("/")

routes = [
    Route("/login", endpoint=login, methods=["GET", "POST"]),
    Route("/logout", endpoint=logout, methods=["GET"]),
]
```

### Protecting Routes

You can protect routes by checking the session:

```python
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import RedirectResponse

class AuthenticationMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request, call_next):
        # List of paths that don't require authentication
        public_paths = ["/", "/login", "/static"]

        # Check if the path requires authentication
        path = request.url.path
        if not any(path.startswith(p) for p in public_paths):
            # Check if user is authenticated
            if "user" not in request.session:
                return RedirectResponse("/login")

        response = await call_next(request)
        return response
```

## Settings Reference

| Setting | Type | Default | Description |
|---------|------|---------|-------------|
| `token_id` | `str` | `None` | Identifier for auth tokens and cookies |
| `token_lifetime` | `int` | `86400` | Token lifetime in seconds |

## Implementation Details

The Auth adapter is implemented in the following files:

- `_base.py`: Defines the base class and settings
- `basic.py`: Provides basic username/password authentication

### Base Class

```python
from acb.config import AdapterBase, Settings

class AuthBaseSettings(Settings):
    token_id: Optional[str] = None
    token_lifetime: int = 86400  # 24 hours

class AuthBase(AdapterBase):
    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Authenticate a user with username and password"""
        raise NotImplementedError()
```

## Customization

You can create a custom authentication adapter for more advanced authentication methods:

```python
# myapp/adapters/auth/oauth.py
from fastblocks.adapters.auth._base import AuthBase, AuthBaseSettings
from pydantic import SecretStr

class OAuthSettings(AuthBaseSettings):
    client_id: str = ""
    client_secret: SecretStr = SecretStr("")
    redirect_uri: str = ""

class OAuth(AuthBase):
    settings: OAuthSettings = None

    async def init(self) -> None:
        # Initialize OAuth client
        pass

    async def authenticate(self, code: str) -> Optional[dict]:
        # Exchange authorization code for access token
        # Validate token and return user info
        pass

    async def get_authorization_url(self) -> str:
        # Generate authorization URL
        pass
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
auth: oauth
```
