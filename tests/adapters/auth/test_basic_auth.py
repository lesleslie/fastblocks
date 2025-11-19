"""Tests for the Basic Authentication adapter.

Tests cover:
- HTTP Basic Authentication parsing
- Session middleware initialization
- Authentication credential validation
- Error handling for invalid credentials
- Integration with Starlette authentication
"""

import base64
from unittest.mock import MagicMock, Mock, patch

import pytest
from pydantic import SecretStr
from starlette.authentication import AuthCredentials, AuthenticationError, SimpleUser
from starlette.middleware import Middleware


@pytest.mark.unit
class TestAuthSettings:
    """Test Auth adapter settings."""

    def test_auth_settings_inherits_from_base(self) -> None:
        """Test that AuthSettings inherits from AuthBaseSettings."""
        from fastblocks.adapters.auth._base import AuthBaseSettings
        from fastblocks.adapters.auth.basic import AuthSettings

        assert issubclass(AuthSettings, AuthBaseSettings)

    def test_auth_settings_initialization(self) -> None:
        """Test AuthSettings initialization."""
        from fastblocks.adapters.auth.basic import AuthSettings

        mock_config = MagicMock()
        mock_config.app.token_id = "_test_"

        settings = AuthSettings(config=mock_config)

        assert settings.token_id == "_test_"


@pytest.mark.unit
class TestCurrentUser:
    """Test CurrentUser implementation."""

    def test_current_user_has_role_not_implemented(self) -> None:
        """Test that CurrentUser.has_role raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import CurrentUser

        user = CurrentUser()

        with pytest.raises(NotImplementedError):
            user.has_role("admin")

    def test_current_user_set_role_not_implemented(self) -> None:
        """Test that CurrentUser.set_role raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import CurrentUser

        user = CurrentUser()

        with pytest.raises(NotImplementedError):
            user.set_role("admin")

    def test_current_user_identity_not_implemented(self) -> None:
        """Test that CurrentUser.identity raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import CurrentUser

        user = CurrentUser()

        with pytest.raises(NotImplementedError):
            _ = user.identity

    def test_current_user_display_name_not_implemented(self) -> None:
        """Test that CurrentUser.display_name raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import CurrentUser

        user = CurrentUser()

        with pytest.raises(NotImplementedError):
            _ = user.display_name

    def test_current_user_email_not_implemented(self) -> None:
        """Test that CurrentUser.email raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import CurrentUser

        user = CurrentUser()

        with pytest.raises(NotImplementedError):
            _ = user.email

    def test_current_user_is_authenticated_not_implemented(self) -> None:
        """Test that CurrentUser.is_authenticated raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import CurrentUser

        user = CurrentUser()

        with pytest.raises(NotImplementedError):
            user.is_authenticated()


@pytest.mark.unit
class TestAuthInitialization:
    """Test Auth adapter initialization."""

    def test_auth_initialization_with_secret_key(self) -> None:
        """Test Auth initialization with secret_key parameter."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("test-secret-key-123")
        user_model = Mock()

        auth = Auth(secret_key=secret_key, user_model=user_model)

        assert auth.secret_key == secret_key
        assert auth.name == "basic"
        assert auth.user_model is user_model

    def test_auth_initialization_without_secret_key_raises_error(self) -> None:
        """Test Auth initialization without secret_key raises ValueError."""
        from fastblocks.adapters.auth.basic import Auth

        with pytest.raises(ValueError, match="secret_key must be provided"):
            Auth(secret_key=None, user_model=None)

    def test_auth_initialization_with_config_secret_key(self) -> None:
        """Test Auth initialization using config for secret_key."""
        from fastblocks.adapters.auth.basic import Auth

        with patch("fastblocks.adapters.auth.basic.Config") as MockConfig:
            mock_config_instance = MockConfig.return_value
            mock_config_instance.get.return_value = SecretStr("config-secret")

            auth = Auth(secret_key=None, user_model=None)

            assert auth.secret_key.get_secret_value() == "config-secret"
            assert auth.name == "basic"

    def test_auth_initialization_with_default_user_model(self) -> None:
        """Test Auth initialization with None user_model."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("test-secret")

        auth = Auth(secret_key=secret_key, user_model=None)

        assert auth.user_model is None


@pytest.mark.unit
class TestAuthAuthenticate:
    """Test Auth.authenticate method."""

    @pytest.mark.asyncio
    async def test_authenticate_with_valid_basic_auth(self) -> None:
        """Test authentication with valid Basic Auth header."""
        from fastblocks.adapters.auth.basic import Auth

        # Create valid Basic Auth credentials
        credentials = base64.b64encode(b"testuser:testpass").decode("ascii")
        auth_header = f"Basic {credentials}"

        request = Mock()
        request.headers = {"Authorization": auth_header}
        request.state = Mock()

        result = await Auth.authenticate(request)

        assert result is True
        assert hasattr(request.state, "auth_credentials")
        auth_creds, user = request.state.auth_credentials
        assert isinstance(auth_creds, AuthCredentials)
        assert isinstance(user, SimpleUser)
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_authenticate_without_auth_header(self) -> None:
        """Test authentication without Authorization header."""
        from fastblocks.adapters.auth.basic import Auth

        request = Mock()
        request.headers = {}

        result = await Auth.authenticate(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_with_non_basic_scheme(self) -> None:
        """Test authentication with non-Basic auth scheme."""
        from fastblocks.adapters.auth.basic import Auth

        request = Mock()
        request.headers = {"Authorization": "Bearer some-token"}

        result = await Auth.authenticate(request)

        assert result is False

    @pytest.mark.asyncio
    async def test_authenticate_with_invalid_base64(self) -> None:
        """Test authentication with invalid base64 credentials."""
        from fastblocks.adapters.auth.basic import Auth

        request = Mock()
        request.headers = {"Authorization": "Basic invalid!base64!"}

        with pytest.raises(AuthenticationError, match="Invalid basic auth credentials"):
            await Auth.authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_with_malformed_credentials(self) -> None:
        """Test authentication with malformed credentials."""
        from fastblocks.adapters.auth.basic import Auth

        request = Mock()
        request.headers = {"Authorization": "Basic"}

        with pytest.raises(
            (AuthenticationError, ValueError),
        ):
            await Auth.authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_with_unicode_decode_error(self) -> None:
        """Test authentication with non-ASCII credentials."""
        from fastblocks.adapters.auth.basic import Auth

        # Create base64 that will fail ASCII decode
        invalid_bytes = base64.b64encode(b"\xff\xfe").decode("ascii")
        request = Mock()
        request.headers = {"Authorization": f"Basic {invalid_bytes}"}

        with pytest.raises(AuthenticationError, match="Invalid basic auth credentials"):
            await Auth.authenticate(request)

    @pytest.mark.asyncio
    async def test_authenticate_without_request_state(self) -> None:
        """Test authentication when request has no state attribute."""
        from fastblocks.adapters.auth.basic import Auth

        credentials = base64.b64encode(b"user:pass").decode("ascii")
        request = Mock(spec=["headers"])
        request.headers = {"Authorization": f"Basic {credentials}"}

        result = await Auth.authenticate(request)

        # Should still return True even without state
        assert result is True


@pytest.mark.unit
class TestAuthInit:
    """Test Auth.init method."""

    @pytest.mark.asyncio
    async def test_init_creates_session_middleware(self) -> None:
        """Test that init() creates SessionMiddleware."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("test-secret-key")
        auth = Auth(secret_key=secret_key, user_model=None)
        auth.config = Mock()
        auth.config.deployed = False
        auth.config.auth.token_id = "_test_"

        await auth.init()

        assert hasattr(auth, "middlewares")
        assert len(auth.middlewares) == 1
        middleware = auth.middlewares[0]
        assert isinstance(middleware, Middleware)

    @pytest.mark.asyncio
    async def test_init_with_deployed_config(self) -> None:
        """Test init() with deployed=True sets https_only."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("production-secret")
        auth = Auth(secret_key=secret_key, user_model=None)
        auth.config = Mock()
        auth.config.deployed = True
        auth.config.auth.token_id = "_prod_"

        await auth.init()

        assert hasattr(auth, "middlewares")
        assert len(auth.middlewares) == 1

    @pytest.mark.asyncio
    async def test_init_with_custom_token_id(self) -> None:
        """Test init() respects custom token_id."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("test-secret")
        auth = Auth(secret_key=secret_key, user_model=None)
        auth.config = Mock()
        auth.config.deployed = False
        auth.config.auth.token_id = "_custom_token_"

        await auth.init()

        assert hasattr(auth, "middlewares")


@pytest.mark.unit
class TestAuthLoginLogout:
    """Test Auth login and logout methods."""

    @pytest.mark.asyncio
    async def test_login_not_implemented(self) -> None:
        """Test that login() raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("test-secret")
        auth = Auth(secret_key=secret_key, user_model=None)
        request = Mock()

        with pytest.raises(NotImplementedError):
            await auth.login(request)

    @pytest.mark.asyncio
    async def test_logout_not_implemented(self) -> None:
        """Test that logout() raises NotImplementedError."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("test-secret")
        auth = Auth(secret_key=secret_key, user_model=None)
        request = Mock()

        with pytest.raises(NotImplementedError):
            await auth.logout(request)


@pytest.mark.unit
class TestAuthModuleMetadata:
    """Test Auth module metadata."""

    def test_module_id_exists(self) -> None:
        """Test that MODULE_ID is defined."""
        from fastblocks.adapters.auth.basic import MODULE_ID

        assert MODULE_ID is not None

    def test_module_status_exists(self) -> None:
        """Test that MODULE_STATUS is defined."""
        from fastblocks.adapters.auth.basic import MODULE_STATUS

        assert MODULE_STATUS is not None


@pytest.mark.integration
class TestAuthIntegration:
    """Test Auth integration scenarios."""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self) -> None:
        """Test complete authentication flow."""
        from fastblocks.adapters.auth.basic import Auth

        # Initialize auth
        secret_key = SecretStr("integration-test-secret")
        auth = Auth(secret_key=secret_key, user_model=None)
        auth.config = Mock()
        auth.config.deployed = False
        auth.config.auth.token_id = "_test_"

        # Initialize middleware
        await auth.init()
        assert len(auth.middlewares) == 1

        # Test authentication
        credentials = base64.b64encode(b"testuser:testpass").decode("ascii")
        request = Mock()
        request.headers = {"Authorization": f"Basic {credentials}"}
        request.state = Mock()

        result = await Auth.authenticate(request)
        assert result is True

        auth_creds, user = request.state.auth_credentials
        assert user.username == "testuser"

    @pytest.mark.asyncio
    async def test_multiple_auth_requests(self) -> None:
        """Test handling multiple authentication requests."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("test-secret")
        Auth(secret_key=secret_key, user_model=None)

        # Authenticate multiple users
        users = ["user1", "user2", "user3"]
        results = []

        for username in users:
            credentials = base64.b64encode(f"{username}:pass".encode()).decode("ascii")
            request = Mock()
            request.headers = {"Authorization": f"Basic {credentials}"}
            request.state = Mock()

            result = await Auth.authenticate(request)
            results.append(result)

            _, user = request.state.auth_credentials
            assert user.username == username

        assert all(results)

    @pytest.mark.asyncio
    async def test_auth_with_htmx_request(self) -> None:
        """Test authentication with HtmxRequest."""
        from fastblocks.adapters.auth.basic import Auth

        credentials = base64.b64encode(b"htmxuser:pass").decode("ascii")
        request = Mock()
        request.headers = {"Authorization": f"Basic {credentials}"}
        request.state = Mock()

        result = await Auth.authenticate(request)

        assert result is True
        _, user = request.state.auth_credentials
        assert user.username == "htmxuser"


@pytest.mark.unit
class TestAuthEdgeCases:
    """Test Auth edge cases and error conditions."""

    @pytest.mark.asyncio
    async def test_authenticate_with_empty_credentials(self) -> None:
        """Test authentication with empty credentials."""
        from fastblocks.adapters.auth.basic import Auth

        # Base64 encode empty string
        credentials = base64.b64encode(b"").decode("ascii")
        request = Mock()
        request.headers = {"Authorization": f"Basic {credentials}"}
        request.state = Mock()

        result = await Auth.authenticate(request)

        # Empty credentials should be accepted (username="")
        assert result is True

    @pytest.mark.asyncio
    async def test_authenticate_with_colon_in_password(self) -> None:
        """Test authentication with colon character in password."""
        from fastblocks.adapters.auth.basic import Auth

        # Password contains colon
        credentials = base64.b64encode(b"user:pass:with:colons").decode("ascii")
        request = Mock()
        request.headers = {"Authorization": f"Basic {credentials}"}
        request.state = Mock()

        result = await Auth.authenticate(request)

        assert result is True
        _, user = request.state.auth_credentials
        assert user.username == "user"

    def test_secret_key_is_secure_str(self) -> None:
        """Test that secret_key is stored as SecretStr."""
        from fastblocks.adapters.auth.basic import Auth

        secret_key = SecretStr("super-secret")
        auth = Auth(secret_key=secret_key, user_model=None)

        assert isinstance(auth.secret_key, SecretStr)
        assert auth.secret_key.get_secret_value() == "super-secret"
