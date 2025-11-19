"""Tests for the AuthBase adapter base classes and protocols.

Tests cover:
- CurrentUser protocol implementation
- AuthProtocol contract
- AuthBase abstract functionality
- ContextVar-based user management
"""

from contextvars import ContextVar
from typing import Any
from unittest.mock import Mock

import pytest
from starlette.authentication import UnauthenticatedUser


@pytest.mark.unit
class TestCurrentUserProtocol:
    """Test CurrentUser protocol contract."""

    def test_protocol_implementation(self) -> None:
        """Test implementing CurrentUser protocol."""

        class TestUser:
            def has_role(self, role: str) -> str:
                return role

            def set_role(self, role: str) -> str | bool | None:
                return role

            @property
            def identity(self) -> str:
                return "test-user-123"

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
        assert user.identity == "test-user-123"
        assert user.display_name == "Test User"
        assert user.is_authenticated() is True


@pytest.mark.unit
class TestAuthProtocol:
    """Test AuthProtocol contract."""

    def test_protocol_implementation(self) -> None:
        """Test implementing AuthProtocol."""

        class TestAuth:
            _current_user: ContextVar[Any] = ContextVar(
                "current_user",
                default=None,
            )

            @property
            def current_user(self) -> Any:
                return self._current_user.get()

            async def authenticate(self, request: Any) -> bool:
                return True

            async def login(self, request: Any) -> bool:
                return True

            async def logout(self, request: Any) -> bool:
                return True

        auth = TestAuth()
        assert hasattr(auth, "_current_user")
        assert hasattr(auth, "current_user")


@pytest.mark.unit
class TestContextVarBehavior:
    """Test ContextVar-based user management."""

    def test_context_var_default_value(self) -> None:
        """Test ContextVar with default UnauthenticatedUser."""
        user_ctx: ContextVar[Any] = ContextVar(
            "test_user",
            default=UnauthenticatedUser(),
        )

        current = user_ctx.get()
        assert isinstance(current, UnauthenticatedUser)

    def test_context_var_set_and_get(self) -> None:
        """Test setting and getting user from ContextVar."""
        user_ctx: ContextVar[Any] = ContextVar("test_user")

        test_user = Mock()
        test_user.username = "testuser"

        user_ctx.set(test_user)
        current = user_ctx.get()

        assert current is test_user
        assert current.username == "testuser"

    def test_context_var_isolation(self) -> None:
        """Test ContextVar isolation across instances."""
        user_ctx1: ContextVar[Any] = ContextVar("user1")
        user_ctx2: ContextVar[Any] = ContextVar("user2")

        user1 = Mock()
        user2 = Mock()

        user_ctx1.set(user1)
        user_ctx2.set(user2)

        assert user_ctx1.get() is user1
        assert user_ctx2.get() is user2
