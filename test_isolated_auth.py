"""Test the specific failing test in isolation."""

import pytest


@pytest.mark.unit
class TestAuthSettings:
    """Test Auth adapter settings."""

    def test_auth_settings_inherits_from_base(self) -> None:
        """Test that AuthSettings inherits from AuthBaseSettings."""
        from fastblocks.adapters.auth._base import AuthBaseSettings
        from fastblocks.adapters.auth.basic import AuthSettings

        assert issubclass(AuthSettings, AuthBaseSettings)
