# Changelog

All notable changes to FastBlocks will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.17.0] - 2025-01-10

### BREAKING CHANGES

- **Dependency Management Modernization**: Migrated from `[project.optional-dependencies]` to `[dependency-groups]` following PEP 735 and modern UV standards
  - ⚠️ Old syntax `uv add "fastblocks[admin]"` **no longer works**
  - ✅ New syntax: `uv add --group admin`
  - All feature groups (admin, monitoring, sitemap) now use dependency groups
  - Zero self-references - eliminates circular dependency errors
  - Full UV compatibility with modern dependency group standards
  - See [MIGRATION-0.17.0.md](./docs/migrations/MIGRATION-0.17.0.md) for upgrade instructions

### Changed

- **Dependency Organization**: Migrated all optional dependencies to dependency groups:
  - Feature groups: admin, monitoring, sitemap
  - Development tools: dev
  - Clear categorization with section headers

### Removed

- `[project.optional-dependencies]` section (replaced by `[dependency-groups]`)

## [0.16.0] - 2025-09-28

### Changed

- Fastblocks (quality: 73/100) - 2025-09-26 08:21:21

### Fixed

- test: Update 55 files

## [0.15.2] - 2025-09-22

### Documentation

- config: Update CHANGELOG, pyproject

## [0.15.1] - 2025-09-21

### Fixed

- test: Update 83 files

## [0.13.2] - 2024-12-15

### Added

- Enhanced null safety in template loaders with robust dependency resolution fallbacks
- Comprehensive uvicorn logging configuration with InterceptHandler integration
- Template reload exclusions in CLI development server configuration
- Improved error handling for ACB adapter registration and retrieval
- Enhanced dependency injection patterns with direct ACB imports
- Lazy loading system for app and logger components with fallback mechanisms

### Changed

- **BREAKING**: Simplified dependency management by using direct ACB imports instead of wrapper system
  - Use `from acb.adapters import import_adapter` instead of internal dependency wrappers
  - Use `from acb.depends import depends` for dependency injection
  - Use `from acb.config import Config` for configuration access
- Improved FastBlocksApp initialization process with streamlined startup
- Enhanced template system with better error handling and null safety
- Updated CLI commands with optimized uvicorn and granian configuration
- Improved middleware stack management with position-based ordering
- Enhanced template loader dependency resolution with fallback mechanisms

### Fixed

- Template loader dependency resolution when ACB adapters are not available
- Null pointer exceptions in template loading when dependencies are missing
- Uvicorn logging conflicts with ACB logging system
- Template reload exclusions for better development experience
- Error handling in adapter registration process
- Dependency injection fallbacks for optional components

### Performance

- Optimized template loader with parallel path checking
- Improved bytecode caching with Redis integration
- Enhanced middleware stack caching and position management
- Reduced startup time with lazy loading for non-critical components

### Developer Experience

- Better error messages for adapter registration failures
- Improved CLI logging configuration for cleaner development output
- Enhanced template reload behavior excluding settings and templates directories
- Comprehensive test coverage for ACB integration changes
- Better documentation for dependency injection patterns

## [0.13.1] - 2024-12-13

### Fixed

- Import errors in middleware module
- Missing type annotations in core modules
- Documentation links and references

## [0.13.0] - 2024-12-10

### Added

- **Direct ACB Imports (v0.13.2+)**: Simplified dependency injection using direct ACB imports
- **Adapter Metadata (v0.14.0+)**: All adapters include static MODULE_ID and MODULE_STATUS for ACB 0.19.0 compliance
- Enhanced middleware system with position-based ordering via MiddlewarePosition enum
- Advanced caching system with rule-based configuration and automatic invalidation
- Cache control middleware for simplified cache header management
- Process time header middleware for request performance monitoring
- Current request middleware for global request access via context variables

### Changed

- **BREAKING**: Dependency injection now uses direct ACB imports instead of wrapper system
- Middleware registration uses position-based system for predictable ordering
- Template system uses modern `Inject[Type]` pattern (ACB 0.25.1+)
- Improved error handling with structured exception hierarchy

### Performance

- 50x faster cache key generation with ACB's CRC32C hashing
- 10x faster content hashing with Blake3
- Enhanced template caching with Redis bytecode cache
- Optimized middleware stack execution

## [0.12.0] - 2024-11-15

### Added

- HTMY component integration alongside Jinja2 templates
- Native HTMX support with HtmxRequest and HtmxResponse classes
- Universal query interface supporting multiple model types
- Sitemap generation with multiple strategies (native, static, dynamic, cached)

### Changed

- Template system now uses `[[` and `]]` delimiters instead of `{{` and `}}`
- Enhanced async template rendering with fragment support

## [0.11.0] - 2024-10-20

### Added

- Initial stable release
- Starlette-based ASGI application framework
- Jinja2 async template system
- ACB integration for dependency injection
- Multiple adapter support (auth, admin, routes, templates)
- Comprehensive CLI for project management
- Built-in middleware stack (CSRF, session, compression, security)

### Features

- Server-side rendering with HTMX focus
- Pluggable adapter architecture
- Multi-database support (SQL and NoSQL)
- Brotli compression and minification
- Type-safe configuration with Pydantic
- Automatic route and component discovery
