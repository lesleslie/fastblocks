"""Classify and validate WebSocket bind addresses for FastBlocks.

Local fallback for the BindAddress enum — mcp-common doesn't ship
one, so fastblocks defines its own here. Mirrors the splashstand-side
implementation at ``splashstand/websocket/binding.py`` so behavior is
identical across the two repos.

Bind targets fall into three categories:

* ``LOOPBACK`` — only reachable from the local host (``127.0.0.0/8``,
  ``::1``, ``localhost``). No capability token required.
* ``PRIVATE_LAN`` — RFC1918 ranges (``10/8``, ``172.16/12``,
  ``192.168/16``) and the IPv6 unique-local prefix ``fc00::/7``. No
  capability token required.
* ``PUBLIC`` — wildcards (``0.0.0.0``, ``::``) and other addresses.
  Requires an explicit capability token before binding.

Constructing a :class:`BindAddress` validates the host against these
rules; invalid hosts raise :class:`ValueError`.
"""

from __future__ import annotations

from enum import Enum
from ipaddress import (
    AddressValueError,
    IPv4Address,
    IPv6Address,
    ip_address,
    ip_network,
)

LOOPBACK_HOSTS: frozenset[str] = frozenset({"localhost"})

_PRIVATE_IPV4_NETWORKS = (
    "10.0.0.0/8",
    "172.16.0.0/12",
    "192.168.0.0/16",
)
_PRIVATE_IPV6_NETWORKS = ("fc00::/7",)


def _is_in_private_lan(host: str) -> bool:
    """RFC1918 + IPv6 unique-local only (no link-local or unspecified)."""
    try:
        addr = ip_address(host)
    except AddressValueError:
        return False
    networks: tuple[str, ...]
    if isinstance(addr, IPv4Address):
        networks = _PRIVATE_IPV4_NETWORKS
    elif isinstance(addr, IPv6Address):
        networks = _PRIVATE_IPV6_NETWORKS
    else:  # pragma: no cover - defensive
        return False
    return any(addr in ip_network(n) for n in networks)


class BindAddressKind(Enum):
    """Classification of a bind target."""

    LOOPBACK = "loopback"
    PRIVATE_LAN = "private_lan"
    PUBLIC = "public"


def _classify(host: str) -> BindAddressKind:
    if host in LOOPBACK_HOSTS:
        return BindAddressKind.LOOPBACK
    try:
        addr = ip_address(host)
    except AddressValueError as exc:
        raise ValueError(f"invalid bind address: {host!r}") from exc

    if addr.is_unspecified:
        return BindAddressKind.PUBLIC
    if addr.is_loopback:
        return BindAddressKind.LOOPBACK
    if _is_in_private_lan(host):
        return BindAddressKind.PRIVATE_LAN
    raise ValueError(
        f"address {host!r} is not loopback, private-LAN, or a wildcard; "
        "explicit public bind is not supported"
    )


class BindAddress:
    """A validated bind target."""

    __slots__ = ("_host", "_kind")

    def __init__(self, host: str) -> None:
        self._host = host
        self._kind = _classify(host)

    @property
    def host(self) -> str:
        return self._host

    @property
    def kind(self) -> BindAddressKind:
        return self._kind

    def requires_capability_token(self) -> bool:
        return self._kind is BindAddressKind.PUBLIC

    def validate(self) -> None:
        if self._kind is BindAddressKind.PUBLIC:
            raise ValueError(
                f"binding to public address {self._host!r} requires an "
                "explicit capability token"
            )

    def __repr__(self) -> str:  # pragma: no cover - debug helper
        return f"BindAddress(host={self._host!r}, kind={self._kind.value!r})"


__all__ = ["BindAddress", "BindAddressKind"]
