# Auth Adapter Threat Model

## Scope

This document covers the **framework's auth-adapter surface** that
consumer applications wire their own provider against. It does NOT
cover the starter's skeleton auth mount (the skeleton's empty
mount introduces no threat surface of its own).

## Trust boundary

The framework exposes a configurable auth adapter resolved through
the Oneiric resolver at `domain="fastblocks", key="auth"`. Consumer
applications register their provider (OAuth, SAML, custom JWT, etc.)
and the framework wires the framework-side integration (routes,
session storage, CSRF tokens tied to sessions, etc.).

## Threat surface

1. **Session storage** — the framework reads/writes session data;
   consumer providers MUST treat session IDs as opaque.
2. **CSRF coupling** — auth state changes (login, logout, MFA) are
   state-changing routes; framework CSRF middleware (D6) MUST apply.
3. **Token validation** — providers MUST validate tokens before the
   framework trusts them; framework surfaces a hook but does not
   validate provider tokens itself.
4. **Redirect URI** — auth callbacks MUST validate the redirect URI
   against an allowlist; framework does not enforce this (provider's
   responsibility).

## Mitigations

- D6 CSRF middleware covers #2.
- D6 security headers (CSP, HSTS, X-Frame-Options) cover session-fixation
  and click-jacking vectors.
- Consumers MUST NOT register a provider without addressing #1, #3, #4.

## Out of scope

- Provider implementation specifics (handled in provider docs)
- WebSocket auth (`fastblocks/websocket/auth.py` env-read-at-import is
  a separate Phase 1.5 follow-up per the WebSocket tech debt noted in
  fastblocks/CLAUDE.md)