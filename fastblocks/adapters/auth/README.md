# Auth Adapter

> **FastBlocks Documentation**: [Main](../../../README.md) | [Core Features](../../README.md) | [Actions](../../actions/README.md) | [Adapters](../README.md)

The Auth adapter provides authentication mechanisms for FastBlocks applications.

## Relationship with ACB

The Auth adapter is a FastBlocks-specific extension that builds on ACB's adapter pattern:

- **ACB Foundation**: Provides the adapter pattern, configuration loading, and dependency injection
- **FastBlocks Extension**: Implements web-specific authentication mechanisms

The Auth adapter uses ACB's configuration system for settings management and leverages ACB's dependency injection for integration with other components like the Templates adapter.

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
Templates = import_adapter("templates")
auth = depends.get(Auth)
templates = depends.get(Templates)

async def login(request):
    if request.method == "POST":
        form = await request.form()
        username = form.get("username")
        password = form.get("password")

        user = await auth.authenticate(username, password)
        if user:
            # Set session data
            request.session["user"] = user.model_dump()
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
    def __init__(self, app):
        super().__init__(app)

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
from acb.config import Settings

class AuthBaseSettings(Settings):
    token_id: str | None = None
    token_lifetime: int = 86400  # 24 hours

class AuthBase(AdapterBase):
    async def authenticate(self, username: str, password: str) -> dict[str, object] | None:
        """Authenticate a user with username and password"""
        raise NotImplementedError()
```

## User Storage and Retrieval

The Auth adapter focuses on authentication, but you'll need to implement user storage and retrieval:

### Using SQLAlchemy

```python
from typing import Optional
from sqlalchemy import Column, Integer, String, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from fastblocks.adapters.auth._base import AuthBase, AuthBaseSettings
import bcrypt

Base = declarative_base()

class User(Base):
    __tablename__ = "users"

    id = Column(Integer, primary_key=True)
    username = Column(String, unique=True, nullable=False)
    email = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)

    def verify_password(self, password: str) -> bool:
        """Verify a password against the stored hash."""
        if isinstance(password, str):
            password = password.encode("utf-8")
        return bcrypt.checkpw(password, self.password_hash.encode("utf-8"))

class DatabaseAuthSettings(AuthBaseSettings):
    db_url: str = "sqlite:///./users.db"

class DatabaseAuth(AuthBase):
    settings: DatabaseAuthSettings | None = None

    async def init(self) -> None:
        """Initialize the database connection."""
        if self.settings is None:
            return

        self.engine = create_engine(self.settings.db_url)
        self.Session = sessionmaker(bind=self.engine)
        Base.metadata.create_all(self.engine)

    async def authenticate(self, username: str, password: str) -> Optional[dict]:
        """Authenticate a user with username and password."""
        session = self.Session()
        try:
            user = session.query(User).filter_by(username=username).first()
            if user and user.verify_password(password):
                return {
                    "id": user.id,
                    "username": user.username,
                    "email": user.email
                }
            return None
        finally:
            session.close()

    async def create_user(self, username: str, email: str, password: str) -> User:
        """Create a new user."""
        session = self.Session()
        try:
            # Hash the password
            password_hash = bcrypt.hashpw(
                password.encode("utf-8"), bcrypt.gensalt()
            ).decode("utf-8")

            # Create user
            user = User(
                username=username,
                email=email,
                password_hash=password_hash
            )

            session.add(user)
            session.commit()
            return user
        finally:
            session.close()
```

### Using Redis for Session Management

```python
import json
import uuid
from datetime import datetime, timedelta
from redis.asyncio import Redis
from fastblocks.adapters.auth._base import AuthBase, AuthBaseSettings

class RedisSessionSettings(AuthBaseSettings):
    redis_url: str = "redis://localhost:6379/0"
    session_prefix: str = "session:"

class RedisSessionAuth(AuthBase):
    settings: RedisSessionSettings | None = None

    async def init(self) -> None:
        """Initialize the Redis connection."""
        if self.settings is None:
            return

        self.redis = Redis.from_url(self.settings.redis_url)

    async def create_session(self, user_data: dict) -> str:
        """Create a new session for the user."""
        session_id = str(uuid.uuid4())
        session_key = f"{self.settings.session_prefix}{session_id}"

        # Set expiration time
        expiry = datetime.now() + timedelta(seconds=self.settings.token_lifetime)

        # Store session data
        session_data = {
            "user": user_data,
            "created_at": datetime.now().isoformat(),
            "expires_at": expiry.isoformat()
        }

        # Save to Redis
        await self.redis.set(
            session_key,
            json.dumps(session_data),
            ex=self.settings.token_lifetime
        )

        return session_id

    async def get_session(self, session_id: str) -> dict | None:
        """Get session data by ID."""
        session_key = f"{self.settings.session_prefix}{session_id}"

        # Get from Redis
        data = await self.redis.get(session_key)
        if data is None:
            return None

        # Parse session data
        session_data = json.loads(data)

        # Check if session is expired
        expires_at = datetime.fromisoformat(session_data["expires_at"])
        if expires_at < datetime.now():
            await self.redis.delete(session_key)
            return None

        return session_data

    async def invalidate_session(self, session_id: str) -> None:
        """Invalidate a session."""
        session_key = f"{self.settings.session_prefix}{session_id}"
        await self.redis.delete(session_key)
```

## Authentication Strategies

### JWT Authentication

```python
import jwt
from datetime import datetime, timedelta
from fastblocks.adapters.auth._base import AuthBase, AuthBaseSettings
from pydantic import SecretStr

class JWTSettings(AuthBaseSettings):
    secret_key: SecretStr = SecretStr("change-me-in-production")
    algorithm: str = "HS256"

class JWTAuth(AuthBase):
    settings: JWTSettings | None = None

    async def create_token(self, user_data: dict) -> str:
        """Create a JWT token for the user."""
        if self.settings is None:
            raise RuntimeError("Settings not initialized")

        # Set expiration time
        expiry = datetime.now() + timedelta(seconds=self.settings.token_lifetime)

        # Create payload
        payload = {
            "sub": str(user_data["id"]),
            "user": user_data,
            "exp": expiry.timestamp(),
            "iat": datetime.now().timestamp()
        }

        # Encode token
        token = jwt.encode(
            payload,
            self.settings.secret_key.get_secret_value(),
            algorithm=self.settings.algorithm
        )

        return token

    async def verify_token(self, token: str) -> dict | None:
        """Verify a JWT token and return the payload."""
        if self.settings is None:
            raise RuntimeError("Settings not initialized")

        try:
            payload = jwt.decode(
                token,
                self.settings.secret_key.get_secret_value(),
                algorithms=[self.settings.algorithm]
            )

            return payload["user"]
        except jwt.ExpiredSignatureError:
            # Token has expired
            return None
        except jwt.InvalidTokenError:
            # Invalid token
            return None
```

## Customization

You can create a custom authentication adapter for more advanced authentication methods:

```python
# myapp/adapters/auth/oauth.py
from fastblocks.adapters.auth._base import AuthBase, AuthBaseSettings
from pydantic import SecretStr
import httpx

class OAuthSettings(AuthBaseSettings):
    client_id: str = ""
    client_secret: SecretStr = SecretStr("")
    redirect_uri: str = ""
    auth_url: str = ""
    token_url: str = ""
    userinfo_url: str = ""

class OAuth(AuthBase):
    settings: OAuthSettings | None = None

    async def init(self) -> None:
        """Initialize the OAuth client."""
        self.http_client = httpx.AsyncClient()

    async def authenticate(self, code: str) -> dict[str, object] | None:
        """Exchange authorization code for access token and user info."""
        if self.settings is None:
            return None

        # Exchange code for token
        token_data = await self.http_client.post(
            self.settings.token_url,
            data={
                "client_id": self.settings.client_id,
                "client_secret": self.settings.client_secret.get_secret_value(),
                "code": code,
                "redirect_uri": self.settings.redirect_uri,
                "grant_type": "authorization_code"
            }
        )

        if token_data.status_code != 200:
            return None

        token = token_data.json()["access_token"]

        # Get user info
        user_data = await self.http_client.get(
            self.settings.userinfo_url,
            headers={"Authorization": f"Bearer {token}"}
        )

        if user_data.status_code != 200:
            return None

        return user_data.json()

    async def get_authorization_url(self, state: str = "") -> str:
        """Generate authorization URL."""
        if self.settings is None:
            return ""

        params = {
            "client_id": self.settings.client_id,
            "redirect_uri": self.settings.redirect_uri,
            "response_type": "code",
            "scope": "openid profile email",
        }

        if state:
            params["state"] = state

        query = "&".join(f"{k}={v}" for k, v in params.items())
        return f"{self.settings.auth_url}?{query}"
```

Then configure your application to use your custom adapter:

```yaml
# settings/adapters.yml
auth: oauth

# settings/auth.yml
auth:
  client_id: "your-client-id"
  client_secret: "your-client-secret"
  redirect_uri: "https://your-app.com/oauth/callback"
  auth_url: "https://auth.provider.com/authorize"
  token_url: "https://auth.provider.com/token"
  userinfo_url: "https://auth.provider.com/userinfo"
```
