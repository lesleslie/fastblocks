# Changelog

All notable changes to FastBlocks will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

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

### Migration Guide

#### Updating Import Patterns

**Before (v0.13.1 and earlier):**

```python
from fastblocks.dependencies import Templates, App
from fastblocks.config import config
```

**After (v0.13.2+):**

```python
from acb.adapters import import_adapter
from acb.depends import depends
from acb.config import Config

Templates = import_adapter("templates")
App = import_adapter("app")
config = depends.get(Config)
```

#### Updating Route Handlers

**Before:**

```python
@depends.inject
async def homepage(request, templates=depends(Templates)):
    return await templates.render_template(request, "index.html")
```

**After:**

```python
@depends.inject
async def homepage(request, templates: Templates = depends()):
    return await templates.app.render_template(request, "index.html")
```

#### Configuration Changes

No configuration file changes are required. The new system maintains backward compatibility at the configuration level while simplifying the import patterns.

### Compatibility

- **Python**: Requires Python 3.13+
- **ACB**: Compatible with ACB 2.x series with enhanced integration
- **Jinja2**: Enhanced compatibility with jinja2-async-environment
- **Starlette**: Full compatibility with Starlette 0.47.1+

### Dependencies

- Updated ACB integration patterns for better performance
- Enhanced jinja2-async-environment compatibility
- Improved uvicorn logging integration
- Better Redis caching integration for templates

## [0.13.1] - Previous Release

### Added

- Previous features and improvements

### Changed

- Previous changes

### Fixed

- Previous bug fixes

______________________________________________________________________

## Release Notes

### Version 0.13.2 Highlights

This release focuses on **dependency management simplification** and **developer experience improvements**. The most significant change is the move from internal dependency wrappers to direct ACB imports, which:

1. **Simplifies the codebase** by removing intermediate abstraction layers
1. **Improves performance** through direct adapter access
1. **Enhances maintainability** by aligning with ACB patterns
1. **Provides better error handling** with explicit fallback mechanisms

The template system has been significantly enhanced with null safety features and better dependency resolution, making FastBlocks more robust in various deployment scenarios.

CLI improvements include better uvicorn logging integration and optimized reload behavior for a smoother development experience.

### Backward Compatibility

While the import patterns have changed, existing FastBlocks applications will continue to work. However, we recommend updating to the new import patterns for better performance and future compatibility.

### Performance Improvements

- Template loading is now more efficient with parallel path checking
- Dependency injection is faster with direct ACB access
- Middleware stack management is optimized with better caching
- Startup time is reduced through lazy loading of optional components

### Testing

This release includes comprehensive test coverage for the ACB integration changes, ensuring stability and reliability of the new dependency management system.
