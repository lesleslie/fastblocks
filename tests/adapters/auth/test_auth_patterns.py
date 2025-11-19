"""Tests for authentication patterns and behaviors.

Tests the core patterns used in authentication without requiring
full module imports. Focuses on:
- ContextVar behavior for user management
- Protocol implementations
- Base64 credential encoding/decoding
- Session middleware patterns
"""

import base64
from contextvars import ContextVar
from typing import Any
from unittest.mock import Mock

import pytest
from pydantic import SecretStr
from starlette.authentication import (
    AuthCredentials,
    SimpleUser,
    UnauthenticatedUser,
)
from starlette.middleware import Middleware
from starlette.middleware.sessions import SessionMiddleware


@pytest.mark.unit
class TestContextVarUserManagement:
    """Test ContextVar-based user management patterns."""

    def test_context_var_with_unauthenticated_default(self) -> None:
        """Test ContextVar with UnauthenticatedUser as default."""
        current_user: ContextVar[Any] = ContextVar(
            "current_user",
            default=UnauthenticatedUser(),
        )

        user = current_user.get()
        assert isinstance(user, UnauthenticatedUser)

    def test_context_var_set_authenticated_user(self) -> None:
        """Test setting authenticated user in ContextVar."""
        current_user: ContextVar[Any] = ContextVar("current_user")

        test_user = Mock()
        test_user.username = "testuser"
        test_user.is_authenticated = True

        current_user.set(test_user)
        retrieved_user = current_user.get()

        assert retrieved_user is test_user
        assert retrieved_user.username == "testuser"
        assert retrieved_user.is_authenticated is True

    def test_context_var_shared_across_class_instances(self) -> None:
        """Test that ContextVar is shared across class instances."""

        class AuthManager:
            _current_user: ContextVar[Any] = ContextVar(
                "shared_user",
                default=UnauthenticatedUser(),
            )

            @property
            def current_user(self) -> Any:
                return self._current_user.get()

        manager1 = AuthManager()
        manager2 = AuthManager()

        test_user = Mock()
        manager1._current_user.set(test_user)

        # Both managers share the same ContextVar
        assert manager2.current_user is test_user


@pytest.mark.unit
class TestBasicAuthCredentials:
    """Test HTTP Basic Auth credential handling."""

    def test_valid_basic_auth_encoding(self) -> None:
        """Test encoding credentials for Basic Auth."""
        username = "testuser"
        password = "testpass"
        credentials = f"{username}:{password}".encode("ascii")
        encoded = base64.b64encode(credentials).decode("ascii")
        auth_header = f"Basic {encoded}"

        assert "Basic" in auth_header
        assert encoded in auth_header

    def test_basic_auth_decoding(self) -> None:
        """Test decoding Basic Auth credentials."""
        username = "testuser"
        password = "testpass"
        credentials = f"{username}:{password}".encode("ascii")
        encoded = base64.b64encode(credentials).decode("ascii")

        decoded = base64.b64decode(encoded).decode("ascii")
        decoded_username, _, decoded_password = decoded.partition(":")

        assert decoded_username == username
        assert decoded_password == password

    def test_basic_auth_with_colon_in_password(self) -> None:
        """Test Basic Auth when password contains colons."""
        username = "user"
        password = "pass:with:colons"
        credentials = f"{username}:{password}".encode("ascii")
        encoded = base64.b64encode(credentials).decode("ascii")

        decoded = base64.b64decode(encoded).decode("ascii")
        decoded_username, _, decoded_password = decoded.partition(":")

        assert decoded_username == username
        assert decoded_password == password

    def test_invalid_base64_raises_error(self) -> None:
        """Test that invalid base64 raises an error."""
        invalid_encoded = "not!valid!base64!"

        with pytest.raises(Exception):  # binascii.Error
            base64.b64decode(invalid_encoded)

    def test_non_ascii_credentials(self) -> None:
        """Test handling of non-ASCII credentials."""
        non_ascii_bytes = b"\xff\xfe"
        encoded = base64.b64encode(non_ascii_bytes).decode("ascii")

        with pytest.raises(UnicodeDecodeError):
            base64.b64decode(encoded).decode("ascii")


@pytest.mark.unit
class TestAuthenticationFlow:
    """Test authentication flow patterns."""

    def test_parse_authorization_header(self) -> None:
        """Test parsing Authorization header."""
        auth_header = "Basic dGVzdHVzZXI6dGVzdHBhc3M="  # testuser:testpass

        scheme, credentials = auth_header.split()

        assert scheme == "Basic"
        assert credentials == "dGVzdHVzZXI6dGVzdHBhc3M="

    def test_create_auth_credentials(self) -> None:
        """Test creating AuthCredentials for authenticated user."""
        credentials = AuthCredentials(["authenticated"])
        user = SimpleUser("testuser")

        assert "authenticated" in credentials.scopes
        assert user.username == "testuser"
        assert user.is_authenticated is True

    def test_unauthenticated_user(self) -> None:
        """Test UnauthenticatedUser properties."""
        user = UnauthenticatedUser()

        assert user.is_authenticated is False

    def test_request_state_auth_storage(self) -> None:
        """Test storing auth credentials in request state."""
        request = Mock()
        request.state = Mock()

        auth_creds = AuthCredentials(["authenticated"])
        user = SimpleUser("testuser")

        request.state.auth_credentials = (auth_creds, user)

        stored_creds, stored_user = request.state.auth_credentials
        assert stored_creds is auth_creds
        assert stored_user is user
        assert stored_user.username == "testuser"


@pytest.mark.unit
class TestSessionMiddleware:
    """Test SessionMiddleware configuration patterns."""

    def test_create_session_middleware(self) -> None:
        """Test creating SessionMiddleware with configuration."""
        secret_key = SecretStr("test-secret-key")
        session_cookie = "_fb_admin"
        https_only = False

        middleware = Middleware(
            SessionMiddleware,
            secret_key=secret_key.get_secret_value(),
            session_cookie=session_cookie,
            https_only=https_only,
        )

        assert middleware.cls is SessionMiddleware
        assert middleware.kwargs["secret_key"] == "test-secret-key"
        assert middleware.kwargs["session_cookie"] == session_cookie
        assert middleware.kwargs["https_only"] is False

    def test_session_middleware_production_config(self) -> None:
        """Test SessionMiddleware with production settings."""
        secret_key = SecretStr("production-secret")
        middleware = Middleware(
            SessionMiddleware,
            secret_key=secret_key.get_secret_value(),
            session_cookie="_prod_session",
            https_only=True,  # Production setting
        )

        assert middleware.kwargs["https_only"] is True

    def test_middleware_list_initialization(self) -> None:
        """Test initializing middleware list."""
        secret_key = SecretStr("test-secret")

        middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key.get_secret_value(),
                session_cookie="_test_",
                https_only=False,
            ),
        ]

        assert len(middlewares) == 1
        assert middlewares[0].cls is SessionMiddleware


@pytest.mark.unit
class TestProtocolPatterns:
    """Test protocol implementation patterns."""

    def test_current_user_protocol_implementation(self) -> None:
        """Test implementing a CurrentUser-like protocol."""

        class TestUser:
            def has_role(self, role: str) -> str:
                return role

            def set_role(self, role: str) -> bool:
                return True

            @property
            def identity(self) -> str:
                return "user-123"

            @property
            def display_name(self) -> str:
                return "Test User"

            @property
            def email(self) -> str:
                return "test@example.com"

            def is_authenticated(
                self,
                request: Any = None,
                config: Any = None,
            ) -> bool:
                return True

        user = TestUser()

        assert user.has_role("admin") == "admin"
        assert user.identity == "user-123"
        assert user.display_name == "Test User"
        assert user.email == "test@example.com"
        assert user.is_authenticated() is True

    def test_auth_protocol_implementation(self) -> None:
        """Test implementing an Auth-like protocol."""

        class TestAuth:
            _current_user: ContextVar[Any] = ContextVar(
                "current_user",
                default=UnauthenticatedUser(),
            )

            @property
            def current_user(self) -> Any:
                return self._current_user.get()

            async def authenticate(self, request: Any) -> bool:
                # Simulate authentication
                self._current_user.set(SimpleUser("testuser"))
                return True

            async def login(self, request: Any) -> bool:
                return await self.authenticate(request)

            async def logout(self, request: Any) -> bool:
                self._current_user.set(UnauthenticatedUser())
                return True

        auth = TestAuth()
        assert isinstance(auth.current_user, UnauthenticatedUser)

    @pytest.mark.asyncio
    async def test_auth_flow_with_protocol(self) -> None:
        """Test complete auth flow using protocol pattern."""

        class TestAuth:
            _current_user: ContextVar[Any] = ContextVar(
                "current_user",
                default=UnauthenticatedUser(),
            )

            @property
            def current_user(self) -> Any:
                return self._current_user.get()

            async def authenticate(self, request: Any) -> bool:
                self._current_user.set(SimpleUser("user"))
                return True

            async def logout(self, request: Any) -> bool:
                self._current_user.set(UnauthenticatedUser())
                return True

        auth = TestAuth()

        # Initially unauthenticated
        assert isinstance(auth.current_user, UnauthenticatedUser)

        # Authenticate
        request = Mock()
        result = await auth.authenticate(request)
        assert result is True
        assert auth.current_user.username == "user"

        # Logout
        await auth.logout(request)
        assert isinstance(auth.current_user, UnauthenticatedUser)


@pytest.mark.unit
class TestSecretKeyHandling:
    """Test SecretStr handling patterns."""

    def test_secret_str_initialization(self) -> None:
        """Test SecretStr initialization."""
        secret = SecretStr("my-secret-key")

        assert isinstance(secret, SecretStr)
        assert secret.get_secret_value() == "my-secret-key"

    def test_secret_str_not_revealed_in_repr(self) -> None:
        """Test that SecretStr doesn't reveal value in repr."""
        secret = SecretStr("super-secret")

        repr_value = repr(secret)
        assert "super-secret" not in repr_value
        assert "SecretStr" in repr_value

    def test_secret_str_used_with_middleware(self) -> None:
        """Test using SecretStr with middleware."""
        secret = SecretStr("middleware-secret")

        middleware = Middleware(
            SessionMiddleware,
            secret_key=secret.get_secret_value(),
            session_cookie="_test_",
        )

        assert middleware.kwargs["secret_key"] == "middleware-secret"


@pytest.mark.integration
class TestAuthIntegrationPatterns:
    """Test authentication integration patterns."""

    @pytest.mark.asyncio
    async def test_complete_basic_auth_flow(self) -> None:
        """Test complete Basic Auth flow."""
        # 1. Encode credentials
        username = "testuser"
        password = "testpass"
        credentials = base64.b64encode(f"{username}:{password}".encode()).decode(
            "ascii"
        )

        # 2. Create request with auth header
        request = Mock()
        request.headers = {"Authorization": f"Basic {credentials}"}
        request.state = Mock()

        # 3. Parse and validate
        auth_header = request.headers["Authorization"]
        scheme, creds = auth_header.split()

        assert scheme == "Basic"

        decoded = base64.b64decode(creds).decode("ascii")
        user, _, pwd = decoded.partition(":")

        # 4. Create auth credentials
        auth_creds = AuthCredentials(["authenticated"])
        simple_user = SimpleUser(user)
        request.state.auth_credentials = (auth_creds, simple_user)

        # 5. Verify
        stored_creds, stored_user = request.state.auth_credentials
        assert stored_user.username == username
        assert stored_user.is_authenticated is True

    def test_middleware_initialization_pattern(self) -> None:
        """Test middleware initialization pattern."""
        secret_key = SecretStr("test-secret")
        token_id = "_test_"
        deployed = False

        middlewares = [
            Middleware(
                SessionMiddleware,
                secret_key=secret_key.get_secret_value(),
                session_cookie=f"{token_id}_admin",
                https_only=bool(deployed),
            ),
        ]

        assert len(middlewares) == 1
        assert middlewares[0].cls is SessionMiddleware
        assert middlewares[0].kwargs["https_only"] is False
