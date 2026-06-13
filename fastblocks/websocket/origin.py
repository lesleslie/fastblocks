"""WebSocket origin allowlist for FastBlocks.

Phase 1.1.c: ``FASTBLOCKS_WS_ALLOWED_ORIGINS`` is a comma-separated
default-deny allowlist. The two helpers here are pure functions (no
WebSocket framework dependency) so the server can wire them through
to whatever WebSocket library it's using without coupling to a
specific implementation.

The default-deny policy is deliberate: an empty allowlist refuses
every connection. Operators who want "any origin" must opt in
explicitly by setting the env var to ``*``.
"""
from __future__ import annotations

import os
from urllib.parse import urlparse


def parse_allowed_origins(env_var: str = "FASTBLOCKS_WS_ALLOWED_ORIGINS") -> list[str]:
    """Read the comma-separated allowlist from the environment.

    Empty / unset env var -> empty list (default-deny). Whitespace
    around each entry is stripped; empty entries (e.g. trailing comma)
    are dropped.
    """
    raw = os.getenv(env_var, "")
    if not raw:
        return []
    return [entry.strip() for entry in raw.split(",") if entry.strip()]


def check_origin(origin: str | None, allowlist: list[str]) -> bool:
    """Return True iff ``origin`` is permitted by ``allowlist``.

    Wildcard semantics: a single-element allowlist of ``"*"`` allows
    every well-formed origin (operator opt-in). An empty allowlist
    denies every origin (default-deny). The match is exact-string,
    scheme-sensitive, and port-sensitive — so
    ``"https://app.example.com"`` does not match
    ``"http://app.example.com"`` and ``"https://app:443"`` does
    not match ``"https://app:8443"``.

    Garbage origins (None, empty, malformed URLs, dangerous schemes
    like ``javascript:``) are denied unconditionally — even when
    ``*`` is in the allowlist. The wildcard applies to
    well-formed http(s) origins, not to arbitrary strings the
    browser might put in the ``Origin`` header.
    """
    if not allowlist:
        return False
    if origin is None or not origin:
        return False
    if not _is_well_formed_url(origin):
        return False

    # ``*`` in the allowlist allows every well-formed origin.
    if allowlist == ["*"] or "*" in allowlist:
        return True

    return origin in allowlist


def _is_well_formed_url(origin: str) -> bool:
    """Return True iff ``origin`` parses as a ``http://`` or ``https://`` URL.

    Rejects garbage strings and dangerous schemes (javascript:, data:,
    file:, vbscript:, etc.). Used by ``check_origin`` to deny
    crafted-origin XSS vectors at the protocol boundary.
    """
    try:
        parsed = urlparse(origin)
    except (ValueError, TypeError):
        return False
    if parsed.scheme not in ("http", "https"):
        return False
    if not parsed.netloc:
        return False
    return True


__all__ = ["check_origin", "parse_allowed_origins"]
