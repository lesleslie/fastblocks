"""Tests for fastblocks.websocket.binding.BindAddress.

Mirrors the splashstand-side tests. BindAddress classifies a host
into LOOPBACK / PRIVATE_LAN / PUBLIC, refuses public binds without
explicit opt-in, and raises ValueError on garbage input.
"""

from __future__ import annotations

import pytest

from fastblocks.websocket.binding import BindAddress, BindAddressKind

# fastblocks.websocket.binding re-exports through fastblocks.websocket
# (the package __init__), which imports fastblocks.websocket.server,
# which imports from mcp_common.websocket (the stub provided by
# tests/conftest.py).
pytestmark = [pytest.mark.unit, pytest.mark.websocket]


@pytest.mark.unit
class TestLoopback:
    def test_loopback_ipv4(self) -> None:
        addr = BindAddress("127.0.0.1")
        assert addr.kind is BindAddressKind.LOOPBACK
        assert addr.requires_capability_token() is False

    def test_loopback_ipv6(self) -> None:
        addr = BindAddress("::1")
        assert addr.kind is BindAddressKind.LOOPBACK
        assert addr.requires_capability_token() is False

    def test_loopback_localhost(self) -> None:
        addr = BindAddress("localhost")
        assert addr.kind is BindAddressKind.LOOPBACK
        assert addr.requires_capability_token() is False


@pytest.mark.unit
class TestPrivateLan:
    @pytest.mark.parametrize(
        "host",
        [
            "10.0.0.5",
            "172.16.0.10",
            "172.31.255.254",
            "192.168.1.42",
            "fc00::1",
        ],
    )
    def test_private_lan_ranges(self, host: str) -> None:
        addr = BindAddress(host)
        assert addr.kind is BindAddressKind.PRIVATE_LAN
        assert addr.requires_capability_token() is False


@pytest.mark.unit
class TestPublic:
    @pytest.mark.parametrize("host", ["0.0.0.0", "::"])
    def test_public_wildcard_requires_capability(self, host: str) -> None:
        addr = BindAddress(host)
        assert addr.kind is BindAddressKind.PUBLIC
        assert addr.requires_capability_token() is True

    def test_validate_raises_on_public(self) -> None:
        addr = BindAddress("0.0.0.0")
        with pytest.raises(ValueError, match="capability token"):
            addr.validate()

    def test_validate_passes_on_loopback(self) -> None:
        # Should not raise
        BindAddress("127.0.0.1").validate()


@pytest.mark.unit
class TestInvalid:
    @pytest.mark.parametrize(
        "host",
        [
            "8.8.8.8",  # public IP
            "169.254.0.1",  # link-local
            "not-an-ip",
            "256.0.0.1",  # out of range
            "172.32.0.1",  # outside 172.16/12
        ],
    )
    def test_invalid_host_raises(self, host: str) -> None:
        with pytest.raises(ValueError):
            BindAddress(host)
