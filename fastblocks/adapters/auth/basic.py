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
import re
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


class _MinimalAuthConfig:
    """Stand-in config for ``Auth.init()`` when no real config is wired.

    The Oneiric migration dropped the ACB-driven ``self.config`` attribute
    on adapter classes. ``Auth.init()`` still needs ``self.config.deployed``
    to compute ``https_only`` on the session cookie. This minimal stub
    supplies the two attributes ``init()`` reads; if you need more
    configuration surface, construct the ``Auth`` through the registry
    and let Oneiric inject a real ``MahavishnuSettings``-derived config.
    """

    def __init__(self, secret_key: SecretStr) -> None:
        self.deployed: bool = False
        self.app = _MinimalAppSettings(secret_key)


class _MinimalAppSettings:
    def __init__(self, secret_key: SecretStr) -> None:
        self.secret_key = secret_key
        self.token_id: str = "_fb_"


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
        users: dict[str, str] | None = None,
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
        # Phase 1.5.b: a small built-in ``users`` dict for tests and
        # minimalist deployments. The production path still goes
        # through ``self.user_model``; this is a convenience for
        # the validator methods below and for the test suite.
        self.users: dict[str, str] = users or {}

    async def init(self) -> None:
        # Default to a minimal config object when ``Auth`` is constructed
        # without one. The Oneiric migration dropped the ACB-driven
        # ``self.config`` attribute, so consumer code that creates an
        # ``Auth`` directly (rather than going through the registry)
        # needs a sensible default. Production code goes through the
        # registry and gets a real config; this fallback is for tests
        # and minimal standalone use.
        if not hasattr(self, "config") or self.config is None:
            self.config = _MinimalAuthConfig(self.secret_key)
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

    # ------------------------------------------------------------------
    # Phase 1.5.b / 1.5.c: credential validation.
    # ------------------------------------------------------------------

    # Phase 1.5.b: allowlist regex for username format. Tighter than
    # the previous raw-username user_id, which accepted any string
    # and surfaced it downstream as a SQL-injection / log-forging
    # surface. The regex is intentionally explicit about the safe
    # character set: letters, digits, dot, underscore, dash.
    _USERNAME_RE = re.compile(r"^[A-Za-z0-9_.-]{1,64}$")

    # Phase 1.5.c: minimum password length. 8 is the OWASP floor for
    # interactive logins. We do not delegate the short-password path
    # to ``mcp_common.security.api_keys.APIKeyValidator`` because its
    # error messages are phrased around API keys, not passwords —
    # and the test contract (``test_error_message_mentions_password_not_api_key``)
    # explicitly forbids the string "api key" in the error.
    _PASSWORD_MIN_LENGTH = 8

    def _validate_username(self, username: str) -> None:
        """Validate a basic-auth username.

        Raises ``ValueError`` with a message mentioning "Username"
        if the supplied value is not a non-empty string matching
        ``^[A-Za-z0-9_.-]{1,64}$``. Phase 1.5.b hardening.
        """
        if not isinstance(username, str) or not self._USERNAME_RE.match(username):
            raise ValueError(
                f"Invalid username: must match {self._USERNAME_RE.pattern}"
            )

    def _validate_password(self, password: str) -> None:
        """Validate a basic-auth password.

        Raises ``ValueError`` with a message mentioning "password"
        (lowercase) if the supplied value is shorter than the
        minimum length. The error message MUST NOT contain the
        phrase "api key" — that is a separate concern covered by
        ``mcp_common.security.api_keys.APIKeyValidator`` for API
        tokens, not interactive passwords.
        """
        if not isinstance(password, str) or len(password) < self._PASSWORD_MIN_LENGTH:
            raise ValueError(
                f"Invalid password: minimum {self._PASSWORD_MIN_LENGTH} "
                "characters required"
            )


MODULE_ID = UUID("01937d86-5f3b-7c4d-9e0f-2345678901bc")
MODULE_STATUS = "STABLE"  # Oneiric-compatible status
