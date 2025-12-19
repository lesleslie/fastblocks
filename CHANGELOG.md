# Changelog

All notable changes to FastBlocks will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.18.7] - 2025-12-19

### Changed

- Update deps, tests

## [0.18.6] - 2025-12-12

### Changed

- Update config, deps

## [0.18.5] - 2025-12-12

### Changed

- Update config, deps, docs

## [0.18.4] - 2025-12-09

### Changed

- Update config, core, deps, docs, tests

## [0.18.3] - 2025-11-26

### Changed

- Update config, core, deps, docs, tests

## [0.18.2] - 2025-11-19

### Changed

- Fastblocks (quality: 71/100) - 2025-11-19 13:24:11
- Update config, core, deps, docs, tests

## [0.18.1] - 2025-11-19

### Added

- Integrate ACB hash actions for 50x performance improvement
- phase4: Add security scanning infrastructure (Task 4.4 partial)

### Changed

- Add CLI test skeleton (needs mocking infrastructure)
- Apply automatic formatting from ruff-format and mdformat
- phase4-task2: Remove 1 unnecessary async for type ignore (153→152)
- phase4-task2: Remove 17 more unnecessary type ignores (170→153)
- phase4-task2: Remove 20 type ignores using explicit casts (152→132)
- phase4-task2: Remove 53 unnecessary type ignores (223→170)
- Update config, core, deps, docs, tests
- Update config, core, docs, tests
- Update documentation

### Fixed

- adapters: Add missing get_stylesheet_links to IconsBase and fix font test
- Add acb.console mock to enable CLI tests
- Async/await improvements - event-based wait and proper task gathering
- docs: Update 26 files
- Fix async mock issues in component tests
- Fix hardcoded absolute paths in structure tests
- Phase 1 improvements - dead code, unused vars, ACB patterns
- phase2: Add await to depends.get() in actions/gather module
- phase2: Add await to depends.get() in actions/sync module
- phase2: Add await to depends.get() in integration files
- phase2: Correct sitemap/routes to use depends.get_sync() instead of Inject
- phase2: Fix coroutine errors in actions/query/parser.py
- phase2: Fix coroutine errors in adapters/app/default.py
- phase2: Fix coroutine errors in adapters/routes/default.py
- phase2: Fix coroutine errors in cli and template filters
- phase2: Fix coroutine errors in filters and adapter modules
- phase2: Fix coroutine errors in sitemap and admin adapters
- phase2: Fix final coroutine errors in middleware.py
- phase2: Fix remaining coroutine errors in actions module
- phase2: Fix remaining coroutine errors in templates and mcp modules
- phase3: Fix systematic test bugs for quick wins
- phase4: Fix all 10 reportUnnecessaryIsInstance errors (195→182)
- phase4: Fix all 17 reportUndefinedVariable errors (211→195)
- phase4: Fix deprecated/unused/constant errors (10 easy wins)
- phase4: Fix remaining sync depends.get() in MCP and templates
- phase4: Fix sync depends.get() and class names in icon/image adapters
- phase4: Fix sync depends.get() in initializers and template registration
- phase4: Reduce type ignores from 129 to 110 (target \<111 achieved)
- phase4: Suppress reportUnusedFunction for template filters (182→142)
- Post-merge cleanup and test fixes
- tests: Add async/await to caching test functions
- tests: Use is_success property instead of success boolean check

### Documentation

- Add JetBrains plugin iframe for custom delimiter support
- Consolidate and cleanup documentation structure
- HIGH PRIORITY README audit fixes
- phase4: Add type system guidelines and migration guide
- phase4: Complete Task 4.3 documentation updates
- phase4: Complete Task 4.4 Security Hardening
- phase4: Mark Task 4.3 complete in IMPROVEMENT_PLAN
- phase4: Update IMPROVEMENT_PLAN with Phase 4 completion (254→142 errors)
- phase4: Update IMPROVEMENT_PLAN with Task 4.2 completion
- Replace iframe with GitHub-compatible plugin badges
- Simplify README, add Kelp UI, expand HTMY info, update comparisons
- Standardize breadcrumb navigation across all READMEs
- Update improvement plan with Phase 1 progress
- Update IMPROVEMENT_PLAN for Phase 3 start
- Update IMPROVEMENT_PLAN for Phase 3 start
- Update IMPROVEMENT_PLAN with Phase 2 completion
- Update IMPROVEMENT_PLAN with Phase 2 progress
- Update IMPROVEMENT_PLAN.md - Phase 3 completed (33% coverage achieved)
- Update MEDIUM PRIORITY adapter READMEs
- Update, cleanup, and consolidate test documentation

### Testing

- Add ACB depends registry cleanup fixture
- Add comprehensive tests for actions sync modules (85 tests)
- Add comprehensive tests for MCP configuration and tools modules
- Comprehensive test suite improvements and enhancements
- coverage: Add comprehensive query parser tests (0% → 43%)
- htmy: Add comprehensive registry and templates tests
- templates: Enhance jinja2 template adapter tests

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
