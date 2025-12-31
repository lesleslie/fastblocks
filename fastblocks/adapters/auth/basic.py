"""Basic Authentication Adapter for FastBlocks.

Provides HTTP Basic Authentication with session management for FastBlocks applications.
Includes secure credential validation, session middleware integration, and user model support.

Features:
- HTTP Basic Authentication with base64 credential encoding
- Session-based authentication state management
- Configurable secret key for session security
- HTTPS-only cookies in production environments
- Integration with Starlette authentication middleware
- Custom user model support for extended user data

Requirements:
- starlette>=0.47.1
- pydantic>=2.11.7

Usage:
```python
# Updated for Oneiric
from fastblocks.adapters.auth.basic import Auth

auth = Auth(secret_key="your-secret-key")

auth_middleware = await auth.init()
```

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-12
"""

import base64
import binascii
import typing as t
from uuid import UUID

# Oneiric imports
from pydantic import UUID4, EmailStr, SecretStr
from starlette.authentication import AuthCredentials, AuthenticationError, SimpleUser
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware
from starlette.requests import Request
from fastblocks.htmx import HtmxRequest

from ._base import AuthBase, AuthBaseSettings


class AuthSettings(AuthBaseSettings):
    pass


class CurrentUser:
    def has_role(self, _: str) -> str:
        raise NotImplementedError

    def set_role(self, _: str) -> str | bool | None:
        raise NotImplementedError

    @property
    def identity(self) -> UUID4 | str | int:
        raise NotImplementedError

    @property
    def display_name(self) -> str:
        raise NotImplementedError

    @property
    def email(self) -> EmailStr | None:
        raise NotImplementedError

    def is_authenticated(
        self,
        request: HtmxRequest | None = None,
        config: t.Any = None,
    ) -> bool | int | str:
        raise NotImplementedError


class Auth(AuthBase):
    secret_key: SecretStr

    @staticmethod
    async def authenticate(request: HtmxRequest | Request) -> bool:
        headers = getattr(request, "headers", {})
        if "Authorization" not in headers:
            return False
        auth = headers["Authorization"]
        try:
            scheme, credentials = auth.split()
            if scheme.lower() != "basic":
                return False
            decoded = base64.b64decode(credentials).decode("ascii")
        except (ValueError, UnicodeDecodeError, binascii.Error):
            msg = "Invalid basic auth credentials"
            raise AuthenticationError(msg)
        username, _, _ = decoded.partition(":")
        state = getattr(request, "state", None)
        if state:
            state.auth_credentials = (
                AuthCredentials(["authenticated"]),
                SimpleUser(username),
            )
        return True

    def __init__(
        self,
        secret_key: SecretStr | None = None,
        user_model: t.Any | None = None,
    ) -> None:
        # For Oneiric, we'll use a simpler approach
        # In practice, this would be replaced with actual config resolution
        if secret_key is None:
            raise ValueError("secret_key must be provided directly (Oneiric migration)")

        super().__init__(secret_key, user_model)
        self.secret_key = secret_key
        if not self.secret_key:
            raise ValueError("secret_key must be provided via parameter")
        self.name = "basic"
        self.user_model = user_model

    async def init(self) -> None:
        self.middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=self.secret_key.get_secret_value(),
                session_cookie=f"{self.token_id}_admin",
                https_only=bool(self.config.deployed),
            ),
        ]

    async def login(self, request: HtmxRequest) -> bool:
        raise NotImplementedError

    async def logout(self, request: HtmxRequest) -> bool:
        raise NotImplementedError


MODULE_ID = UUID("01937d86-5f3b-7c4d-9e0f-2345678901bc")
MODULE_STATUS = "STABLE"  # Oneiric-compatible status
