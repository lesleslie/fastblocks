"""Tests for basic auth username + password validation (Phase 1.5.b + 1.5.c)."""

from __future__ import annotations

import pytest
from pydantic import SecretStr
from fastblocks.adapters.auth.basic import Auth


@pytest.mark.unit
class TestUsernameValidation:
    def test_rejects_malformed_username_with_at_sign(self) -> None:
        auth = Auth(
            secret_key=SecretStr("test-secret-key-must-be-long-enough"),
            users={"alice": "wonderland"},
        )
        # user@evil contains '@' which is not in ^[A-Za-z0-9_.-]{1,64}$
        with pytest.raises(ValueError, match="[Uu]sername"):
            auth._validate_username("user@evil")

    def test_rejects_empty_username(self) -> None:
        auth = Auth(
            secret_key=SecretStr("test-secret-key-must-be-long-enough"),
            users={"alice": "wonderland"},
        )
        with pytest.raises(ValueError, match="[Uu]sername"):
            auth._validate_username("")

    def test_rejects_username_too_long(self) -> None:
        auth = Auth(
            secret_key=SecretStr("test-secret-key-must-be-long-enough"),
            users={"alice": "wonderland"},
        )
        with pytest.raises(ValueError, match="[Uu]sername"):
            auth._validate_username("a" * 65)

    def test_accepts_valid_username(self) -> None:
        auth = Auth(
            secret_key=SecretStr("test-secret-key-must-be-long-enough"),
            users={"alice": "wonderland"},
        )
        # Should not raise
        auth._validate_username("alice.smith-01_v2")


@pytest.mark.unit
class TestPasswordValidation:
    def test_rejects_short_password(self) -> None:
        auth = Auth(
            secret_key=SecretStr("test-secret-key-must-be-long-enough"),
            users={"alice": "wonderland"},
        )
        with pytest.raises(ValueError, match="[Pp]assword"):
            auth._validate_password("short")

    def test_error_message_mentions_password_not_api_key(self) -> None:
        auth = Auth(
            secret_key=SecretStr("test-secret-key-must-be-long-enough"),
            users={"alice": "wonderland"},
        )
        with pytest.raises(ValueError) as excinfo:
            auth._validate_password("short")
        message = str(excinfo.value)
        assert "password" in message.lower()
        assert "api key" not in message.lower()

    def test_accepts_valid_password(self) -> None:
        auth = Auth(
            secret_key=SecretStr("test-secret-key-must-be-long-enough"),
            users={"alice": "wonderland"},
        )
        # Should not raise
        auth._validate_password("MyP@ssw0rd!")
