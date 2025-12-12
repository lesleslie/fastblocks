# FastBlocks Architecture Guide

> **FastBlocks Documentation**: [Main](../README.md) | [Core Features](../README.md#fastblocks) | [Actions](../fastblocks/actions/README.md) | [Adapters](../fastblocks/adapters/README.md)
>
> _Last reviewed: 2025-11-19_

## Layered Overview

FastBlocks sits between Starlette and application code: Starlette delivers the ASGI runtime, while FastBlocks layers on HTMX-friendly rendering, request helpers, and middleware. Underneath, [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb) provides dependency injection, configuration management, and the adapter pattern that powers FastBlocks’ pluggable components.

```
User App → FastBlocks → Starlette + ACB → Python Standard Library
```

## Relationship with Starlette

FastBlocks extends Starlette instead of reinventing the ASGI stack:

- **Class Extension**: The `FastBlocks` application extends Starlette’s `Starlette` class, inheriting routing, middleware, and ASGI lifecycle management.
- **Enhanced Request Handling**: `HtmxRequest` augments Starlette requests with HTMX metadata (`HX-Request`, swaps, triggers).
- **Middleware**: Specialized middleware layers (HTMX, security headers, Brotli, caching hooks) stack on top of Starlette’s middleware system.
- **Template Integration**: Async template rendering slots into Starlette responses without custom ASGI glue, thanks to `starlette-async-jinja`.
- **Error Handling**: Template-aware exception responses build on Starlette’s exception handlers for SSR friendliness.

## Relationship with ACB

ACB supplies the infrastructure glue that keeps adapters swappable and dependencies explicit:

- **Dependency Injection**: `@depends.inject` and `Inject[Type]` hints come directly from ACB, giving FastBlocks type-safe DI with automatic fallbacks.
- **Configuration System**: Settings files and environment overrides flow through ACB’s configuration loader.
- **Adapter Pattern**: FastBlocks’ adapters (templates, auth, admin, routes, sitemap, etc.) are ACB adapters under the hood.
- **Component Boundaries**: ACB’s adapter registry lets FastBlocks’ components evolve independently or be replaced entirely.

### Modern ACB Integration (v0.14.0+, ACB 0.25.1+)

- Use `import_adapter("templates")` (or similar) to obtain adapter classes.
- Annotate dependencies with `Inject[MyAdapter]` inside `@depends.inject` endpoints for type safety.
- When migrating from legacy patterns, see [`docs/migrations/MIGRATION-0.17.0.md`](./migrations/MIGRATION-0.17.0.md) for modern DI examples and dependency-group notes.

## Server-Side Rendering with HTMX

FastBlocks is optimized for SSR-first applications that enhance progressively with HTMX:

- **Reduced Complexity**: Keep business logic on the server and skip heavy SPA frameworks.
- **Performance**: Async templates, caching, and compression deliver fast first-paint times.
- **SEO-Friendly**: Full HTML responses keep search engines happy without special handling.
- **Progressive Enhancement**: HTMX swaps incrementally enhance otherwise functional pages.
- **Use Cases**: Admin dashboards, CMS, internal tools, and line-of-business apps where data integrity matters more than flashy JS.

## Project Structure

The repository follows a component-based layout that mirrors ACB’s adapter model:

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

Refer back to this document whenever you need to explain how FastBlocks layers on Starlette + ACB, or when onboarding teammates who need the architectural context before diving into adapters and actions.
