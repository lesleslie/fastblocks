# Testing FastBlocks

**Last Updated**: November 2025
**Test Suite Status**: ✅ Comprehensive with markers, 900+ tests, 42% coverage threshold

This document provides comprehensive information about running, organizing, and writing tests for the FastBlocks project.

## Table of Contents

- [Quick Start](#quick-start)
- [Test Organization](#test-organization)
- [Running Tests](#running-tests)
- [Writing Tests](#writing-tests)
- [Mocking Guidelines](#mocking-guidelines)
- [Test Configuration](#test-configuration)
- [Troubleshooting](#troubleshooting)

______________________________________________________________________

## Quick Start

### Running All Tests

```bash
# Using pytest directly
python -m pytest

# Using UV (recommended)
uv run pytest

# With verbose output
uv run pytest -v

# With coverage
uv run pytest --cov=fastblocks
```

### Running Specific Test Types

```bash
# Run only unit tests (~90% of test suite)
pytest -m unit

# Run only integration tests (~10% of test suite)
pytest -m integration

# Run both unit and integration
pytest -m "unit or integration"

# Exclude integration tests (faster)
pytest -m "not integration"
```

### Running Specific Tests

```bash
# Run tests in a specific directory
pytest tests/adapters/templates/

# Run a specific test file
pytest tests/test_exceptions.py

# Run a specific test function
pytest tests/test_exceptions.py::test_starlette_caches_exception

# Run tests matching a pattern
pytest -k "test_auth"
```

______________________________________________________________________

## Test Organization

The FastBlocks test suite follows a structured organization with clear separation between unit and integration tests.

### Directory Structure

```
tests/
├── conftest.py                 # Global test configuration & fixtures
├── TESTING.md                  # This file
├── adapters/                   # Adapter-specific tests
│   ├── admin/                  # Admin adapter tests
│   ├── app/                    # App adapter tests
│   ├── auth/                   # Authentication tests (NEW)
│   ├── fonts/                  # Font adapter tests
│   ├── icons/                  # Icon adapter tests
│   ├── images/                 # Image adapter tests
│   ├── routes/                 # Route adapter tests
│   ├── sitemap/                # Sitemap tests
│   ├── styles/                 # Style adapter tests
│   └── templates/              # Template adapter tests (extensive)
├── actions/                    # Action tests
│   ├── gather/                 # Gather action tests
│   ├── minify/                 # Minify action tests
│   ├── query/                  # Query action tests
│   └── sync/                   # Sync action tests
├── mcp/                        # MCP server tests
├── performance/                # Performance benchmarks
├── test_*.py                   # Root-level feature tests
└── patch_site_packages.py      # ACB patching utility
```

### Test Categories

#### Unit Tests (`@pytest.mark.unit`)

**Characteristics**:

- Test individual functions/classes in isolation
- Fast execution (< 1 second each)
- Heavy use of mocks and fixtures
- No external dependencies
- ~810 tests (90% of suite)

**Examples**:

- `tests/test_exceptions.py` - Exception handling
- `tests/test_caching.py` - Cache functionality
- `tests/adapters/auth/test_auth_patterns.py` - Auth patterns
- `tests/adapters/templates/test_jinja2.py` - Template rendering

#### Integration Tests (`@pytest.mark.integration`)

**Characteristics**:

- Test interaction between components
- May involve multiple modules
- Test real workflows and scenarios
- ~90 tests (10% of suite)

**Examples**:

- `tests/test_validation_integration.py` - Validation service integration
- `tests/test_events_integration.py` - Event system integration
- `tests/test_health_integration.py` - Health check integration
- `tests/test_workflows_integration.py` - Workflow orchestration

#### Performance Tests (`@pytest.mark.benchmark`)

**Characteristics**:

- Performance benchmarks
- Execution time measurements
- Resource usage tracking

**Examples**:

- `tests/performance/test_performance_verification.py`
- `tests/performance/test_template_performance.py`

### Test File Naming Convention

- **Unit tests**: `test_<feature>.py`
- **Integration tests**: `test_<feature>_integration.py`
- **Comprehensive tests**: `test_<feature>_comprehensive.py`
- **Adapter tests**: `test_<adapter_name>.py`

______________________________________________________________________

## Running Tests

### Basic Test Execution

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run with extra verbosity (show individual test names)
pytest -vv

# Stop at first failure
pytest -x

# Show print statements
pytest -s

# Run last failed tests
pytest --lf

# Run tests in parallel (requires pytest-xdist)
pytest -n auto
```

### Test Selection by Markers

```bash
# Unit tests only (fast)
pytest -m unit

# Integration tests only
pytest -m integration

# Performance benchmarks only
pytest -m benchmark

# Slow tests (can be skipped)
pytest -m slow
pytest -m "not slow"  # Skip slow tests

# Combine markers with OR
pytest -m "unit or integration"

# Combine markers with AND
pytest -m "unit and asyncio"

# Exclude markers with NOT
pytest -m "not integration"
```

### Coverage Reporting

```bash
# Run with coverage
pytest --cov=fastblocks

# Coverage with HTML report
pytest --cov=fastblocks --cov-report=html

# Coverage with missing lines
pytest --cov=fastblocks --cov-report=term-missing

# Enforce coverage threshold (42% minimum)
pytest --cov=fastblocks --cov-fail-under=42
```

### Test Output Control

```bash
# Show print output
pytest -s

# Capture logs
pytest --log-cli-level=INFO

# Show locals on failure
pytest -l

# Show test durations
pytest --durations=10

# Quiet mode
pytest -q
```

### Parallel Execution

FastBlocks tests support parallel execution using pytest-xdist:

```bash
# Run tests in parallel (auto-detected CPU count)
pytest

# Explicitly specify number of workers
pytest -n 4

# Run tests grouped by file (recommended for FastBlocks)
pytest --dist=loadfile
```

______________________________________________________________________

## Writing Tests

### Test Class Structure

```python
import pytest
from unittest.mock import Mock, AsyncMock, patch


@pytest.mark.unit  # Add marker
class TestMyFeature:
    """Test MyFeature functionality."""

    @pytest.mark.asyncio  # For async tests
    async def test_basic_functionality(self) -> None:
        """Test basic functionality."""
        # Arrange
        mock_dependency = Mock()

        # Act
        result = await my_function(mock_dependency)

        # Assert
        assert result is not None
        mock_dependency.method.assert_called_once()
```

### Test Function Structure

```python
@pytest.mark.unit
@pytest.mark.asyncio
async def test_standalone_feature() -> None:
    """Test standalone feature."""
    # Arrange - Set up test data
    test_data = {"key": "value"}

    # Act - Execute the test
    result = await process_data(test_data)

    # Assert - Verify results
    assert result["key"] == "processed_value"
```

### Fixture Usage

```python
@pytest.fixture
def mock_config():
    """Provide mock configuration."""
    config = Mock()
    config.setting = "test_value"
    return config


@pytest.mark.unit
def test_with_fixture(mock_config):
    """Test using fixture."""
    assert mock_config.setting == "test_value"
```

### Integration Test Example

```python
@pytest.mark.integration
class TestAuthenticationFlow:
    """Test complete authentication workflow."""

    @pytest.mark.asyncio
    async def test_full_auth_flow(self) -> None:
        """Test complete login/logout flow."""
        # Test spans multiple components
        auth = Auth(secret_key=SecretStr("test"))
        await auth.init()

        # Authenticate
        request = create_test_request()
        result = await auth.authenticate(request)
        assert result is True

        # Verify session
        assert auth.current_user.is_authenticated
```

### Best Practices

1. **One Test, One Assertion**: Each test should verify one specific behavior
1. **Clear Test Names**: Use descriptive names that explain what is being tested
1. **Arrange-Act-Assert**: Follow the AAA pattern for test structure
1. **Use Type Hints**: All test functions should include return type hints
1. **Document Tests**: Include docstrings explaining test purpose
1. **Isolate Tests**: Each test should be independent and not rely on others
1. **Use Markers**: Always add `@pytest.mark.unit` or `@pytest.mark.integration`

______________________________________________________________________

## Mocking Guidelines

### Core Mocking Principles

**CRITICAL**: Tests should **NEVER** create actual files, directories, or access the filesystem. Use the comprehensive mocking framework provided.

### Available Mock Classes

The test suite provides pre-built mock classes in `conftest.py`:

```python
# Core Mocks
MockAdapter  # Mock adapter implementation
MockConfig  # Configuration mock with nested structures
MockSettings  # Settings with proper load() method
MockAsyncPath  # Async path operations (no filesystem access)

# Template Mocks
MockTemplates  # Template adapter mock
MockTemplateRenderer  # Async template rendering
MockTemplateFilters  # Template filter implementation

# Storage Mocks
MockCache  # In-memory cache
MockStorage  # In-memory storage

# ACB Mocks
MockAdapters  # Adapters registry mock
MockConfigModule  # Full config module mock
```

### Available Fixtures

The test suite also provides reusable pytest fixtures in `conftest.py`:

```python
mock_config()  # Consistent mock configuration
mock_templates()  # Pre-configured mock templates adapter
mock_request()  # Mock HTTP request
mock_response()  # Mock HTTP response
mock_fastblocks_app()  # Mock FastBlocks application
```

### Test Utilities

Additional testing utilities are available in `tests/test_utils.py`:

```python
TestClient()  # Simplified test client for app requests
create_mock_request()  # Create mock requests with specific parameters
create_mock_response()  # Create mock responses with specific parameters
async_test()  # Decorator to run async tests
create_mock_config_with_values()  # Create config with custom values
create_mock_app_with_middleware()  # Create mock app with middleware support
```

````

### Using MockAsyncPath

```python
from tests.conftest import MockAsyncPath


@pytest.mark.unit
async def test_file_operations():
    """Test file operations without filesystem access."""
    path = MockAsyncPath("/fake/path/file.txt")

    # All operations are mocked
    exists = await path.exists()  # Returns True
    is_file = await path.is_file()  # Checks extension
    is_dir = await path.is_dir()  # Returns opposite of is_file

    # Async iteration
    async for item in path.iterdir():
        print(item)  # No items by default
````

### Mocking ACB Dependencies

```python
import sys
import types
from unittest.mock import MagicMock


@pytest.fixture
def mock_acb():
    """Mock ACB module."""
    mock_acb_module = types.ModuleType("acb")
    mock_depends = types.ModuleType("acb.depends")

    # Create dependency injection mock
    depends = MagicMock()
    depends.get = MagicMock(return_value=Mock())
    depends.set = MagicMock()
    depends.inject = lambda f: f  # Pass-through decorator

    setattr(mock_depends, "depends", depends)
    setattr(mock_acb_module, "depends", mock_depends)

    sys.modules["acb"] = mock_acb_module
    sys.modules["acb.depends"] = mock_depends

    return mock_acb_module
```

### Async Mock Patterns

```python
from unittest.mock import AsyncMock


@pytest.mark.unit
@pytest.mark.asyncio
async def test_async_function():
    """Test async function with AsyncMock."""
    # Create async mock
    mock_service = AsyncMock()
    mock_service.fetch_data.return_value = {"data": "value"}

    # Use mock
    result = await mock_service.fetch_data("key")

    # Verify
    assert result == {"data": "value"}
    mock_service.fetch_data.assert_awaited_once_with("key")
```

### Patching with Context Managers

```python
from unittest.mock import patch


@pytest.mark.unit
def test_with_patch():
    """Test with patched module."""
    with patch("fastblocks.module.function") as mock_func:
        mock_func.return_value = "mocked"

        result = function_under_test()

        assert result == "mocked"
        mock_func.assert_called_once()
```

______________________________________________________________________

## Test Configuration

### pytest Configuration (pyproject.toml)

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
timeout = 300  # 5 minutes per test
testpaths = ["tests"]
python_files = ["test_*.py"]
python_classes = ["Test*"]
python_functions = ["test_*"]

# Markers
markers = [
    "unit: marks test as a unit test",
    "integration: marks test as an integration test",
    "benchmark: marks test as a performance test",
]

# Async configuration
asyncio_default_fixture_loop_scope = "function"
```

### Coverage Configuration

```toml
[tool.coverage.run]
source = ["fastblocks"]
omit = [
    "*/tests/*",
    "*/site-packages/*",
    "*/__pycache__/*",
    "*/__init__.py",
]

[tool.coverage.report]
fail_under = 42  # 42% minimum coverage
exclude_also = [
    "pragma: no cover",
    "def __repr__",
    "raise NotImplementedError",
    "if __name__ == .__main__.:",
    "pass",
    "@abstractmethod",
    "@overload",
    "if TYPE_CHECKING:",
    "class .*\\bProtocol\\):",
]
```

### conftest.py Configuration

The global `conftest.py` provides:

1. **ACB Module Patching**: Prevents filesystem access
1. **Mock Classes**: Comprehensive mocking framework
1. **Fixtures**: Reusable test components
1. **Module Cleanup**: Ensures test isolation

______________________________________________________________________

## Troubleshooting

### Common Issues and Solutions

#### Test Collection Failures

**Symptom**: Tests not being collected

**Solutions**:

```bash
# Verify test discovery
pytest --collect-only

# Check for syntax errors
pytest --tb=short

# Verify markers are defined
pytest --markers
```

#### Import Errors

**Symptom**: `ModuleNotFoundError` or `ImportError`

**Solutions**:

```python
# Add module mocking in conftest.py or test file
import sys
import types

mock_module = types.ModuleType("missing_module")
sys.modules["missing_module"] = mock_module
```

#### Async Test Failures

**Symptom**: `RuntimeError: no running event loop`

**Solutions**:

```python
# Ensure @pytest.mark.asyncio is present
@pytest.mark.asyncio
async def test_async_function(): ...


# Or use pytest-asyncio auto mode (already configured)
```

#### FileNotFoundError

**Symptom**: Tests trying to access real files

**Solutions**:

```python
# Use MockAsyncPath instead of real paths
from tests.conftest import MockAsyncPath

path = MockAsyncPath("/fake/path")

# Or patch the file operation
with patch("pathlib.Path.exists", return_value=True):
    ...
```

#### Coverage Threshold Failures

**Symptom**: `FAIL Required test coverage of 42% not reached`

**Solutions**:

```bash
# Run full test suite (not just one test)
pytest --cov=fastblocks

# Check coverage report
pytest --cov=fastblocks --cov-report=term-missing

# Add more tests or exclude uncoverable code
```

#### Slow Tests

**Symptom**: Tests taking too long

**Solutions**:

```bash
# Find slowest tests
pytest --durations=10

# Run only unit tests (faster)
pytest -m unit

# Run tests in parallel
pytest -n auto
```

### ACB-Related Issues

#### Settings File Not Found

**Symptom**: `FileNotFoundError: settings/debug.yml`

**Solution**: Ensure ACB modules are properly mocked in `conftest.py`

#### AsyncPath Iterator Issues

**Symptom**: `'async for' requires an object with __aiter__ method`

**Solution**: Use `MockAsyncPath` which implements proper async iterator protocol

#### Module Patch Issues

**Symptom**: Real ACB modules being imported

**Solution**: Patch modules before any imports:

```python
import sys
import types

# Patch BEFORE other imports
sys.modules["acb"] = types.ModuleType("acb")

from fastblocks import something  # Now safe
```

______________________________________________________________________

## Test Statistics

### Current Test Suite (as of November 2025)

| Metric | Value |
|--------|-------|
| **Total Tests** | ~900+ tests |
| **Unit Tests** | ~810 tests (90%) |
| **Integration Tests** | ~90 tests (10%) |
| **Performance Tests** | ~15 benchmarks |
| **Test Files** | 76 files |
| **Coverage Threshold** | 42% minimum |
| **Marker Coverage** | 100% |
| **Auth Tests** | 40+ tests (NEW) |

### Test Execution Times

- **Full Suite**: ~30-45 seconds
- **Unit Tests Only**: ~20-30 seconds
- **Integration Tests**: ~10-15 seconds
- **Single Test File**: 1-5 seconds

______________________________________________________________________

## Additional Resources

### Tools

- **pytest**: Test framework - https://docs.pytest.org/
- **pytest-asyncio**: Async test support - https://pytest-asyncio.readthedocs.io/
- **pytest-cov**: Coverage plugin - https://pytest-cov.readthedocs.io/
- **pytest-xdist**: Parallel execution - https://pytest-xdist.readthedocs.io/
- **pytest-mock**: Mocking utilities - https://pytest-mock.readthedocs.io/

### Documentation

- **FastBlocks README**: `/README.md`
- **CLAUDE.md**: AI assistant guidance
- **ACB Documentation**: https://github.com/lesleslie/acb
- **Starlette Testing**: https://www.starlette.io/testclient/

### Getting Help

- **GitHub Issues**: Report bugs and request features
- **Test Failures**: Check this TESTING.md troubleshooting section
- **Coverage Reports**: Use `pytest --cov-report=html` for detailed analysis

______________________________________________________________________

## Changelog

### November 2025 - Major Test Suite Improvements

- ✅ Added pytest markers to 513+ tests
- ✅ Created 40+ authentication adapter tests
- ✅ Re-enabled 41 integration tests (events, health)
- ✅ Raised coverage threshold from 31% to 42%
- ✅ Improved test documentation
- ✅ Enhanced coverage reporting
- ✅ Consolidated test organization

### Previous Updates

- Added comprehensive template adapter tests
- Implemented MockAsyncPath for filesystem mocking
- Created ACB module patching system
- Established test isolation patterns
