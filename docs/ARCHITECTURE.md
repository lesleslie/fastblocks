# FastBlocks Architecture Guide

> **FastBlocks Documentation**: [Main](../README.md) | [Core Features](../README.md#fastblocks) | [Actions](../fastblocks/actions/README.md) | [Adapters](../fastblocks/adapters/README.md)
>
> _Last reviewed: 2026-08-19_

## Layered Overview

FastBlocks sits between Starlette and application code: Starlette delivers the ASGI runtime, while FastBlocks layers on HTMX-friendly rendering, request helpers, and middleware. Underneath, [Oneiric](https://github.com/lesleslie/oneiric) provides dependency injection, configuration management, and the adapter pattern that powers FastBlocks' pluggable components.

```
User App → FastBlocks → Starlette + Oneiric → Python Standard Library
```

## Relationship with Starlette

FastBlocks extends Starlette instead of reinventing the ASGI stack:

- **Class Extension**: The `FastBlocks` application extends Starlette’s `Starlette` class, inheriting routing, middleware, and ASGI lifecycle management.
- **Enhanced Request Handling**: `HtmxRequest` augments Starlette requests with HTMX metadata (`HX-Request`, swaps, triggers).
- **Middleware**: Specialized middleware layers (HTMX, security headers, Brotli, caching hooks) stack on top of Starlette’s middleware system.
- **Template Integration**: Async template rendering slots into Starlette responses without custom ASGI glue, thanks to `starlette-async-jinja`.
- **Error Handling**: Template-aware exception responses build on Starlette’s exception handlers for SSR friendliness.

## Relationship with Oneiric

Oneiric supplies the infrastructure glue that keeps adapters swappable and dependencies explicit:

- **Dependency Injection**: `get_resolver()` and `resolve_component_async()` are the canonical Oneiric entry points (see `fastblocks/core/resolver.py`).
- **Configuration System**: Settings files and environment overrides flow through Oneiric's configuration loader (`oneiric.core.config.OneiricSettings`).
- **Adapter Pattern**: FastBlocks' adapters (templates, auth, admin, routes, sitemap, etc.) are registered as Oneiric candidates and resolved via the shared resolver.
- **Component Boundaries**: Oneiric's resolver lets FastBlocks' components evolve independently or be replaced entirely.

### Modern Oneiric Integration (v0.20.0+, Oneiric 0.x)

- Use `get_resolver()` to obtain the shared `oneiric.core.resolution.Resolver` singleton.
- Resolve components with `await resolve_component_async(resolver, "fastblocks", "templates")` from async code (use `resolve_component` from sync code).
- For migration notes from earlier versions, see `docs/migrations/0.7-to-0.8.md`.

## Server-Side Rendering with HTMX

FastBlocks is optimized for SSR-first applications that enhance progressively with HTMX:

- **Reduced Complexity**: Keep business logic on the server and skip heavy SPA frameworks.
- **Performance**: Async templates, caching, and compression deliver fast first-paint times.
- **SEO-Friendly**: Full HTML responses keep search engines happy without special handling.
- **Progressive Enhancement**: HTMX swaps incrementally enhance otherwise functional pages.
- **Use Cases**: Admin dashboards, CMS, internal tools, and line-of-business apps where data integrity matters more than flashy JS.

## Project Structure

The repository follows a component-based layout that mirrors Oneiric's adapter model:

```
fastblocks/
├── actions/         # Utility functions (minify, gather, query, etc.)
├── adapters/        # Integration modules for external systems
│   ├── app/         # Application configuration
│   ├── auth/        # Authentication adapters
│   ├── admin/       # Admin interface adapters
│   ├── routes/      # Routing adapters
│   ├── sitemap/     # Sitemap generation
│   └── templates/   # Template engine adapters
├── applications.py  # FastBlocks application class
├── middleware.py    # ASGI middleware components
└── ...
```

Refer back to this document whenever you need to explain how FastBlocks layers on Starlette + Oneiric, or when onboarding teammates who need the architectural context before diving into adapters and actions.
