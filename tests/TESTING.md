# Testing FastBlocks

This document provides information about running tests for the FastBlocks project.

## Running Tests

### Using pytest

The recommended way to run tests is to use pytest directly:

```bash
python -m pytest
```

You can pass additional pytest arguments:

```bash
python -m pytest -v                # Run with verbose output
python -m pytest tests/adapters/templates/  # Run specific tests
python -m pytest --cov=fastblocks  # Run tests with coverage information
```

## Test Configuration

The test configuration is defined in `pyproject.toml` and `tests/conftest.py`. The tests use pytest fixtures to mock dependencies and prevent file system operations during testing.

## Mocking Guidelines

### Avoiding File System Operations

Tests should **never** create actual files, directories, or settings during test execution. Instead, use the mocking framework provided in the project:

- `MockAdapter`: A mock implementation of the adapter interface with proper path attributes
- `MockTemplateRenderer`: Handles template rendering and caching for tests
- `MockTemplates`: Provides mock functionality for template operations
- `MockTemplateFilters`: Implements template filters for testing
- `MockCache`: A memory-based cache implementation
- `MockStorage`: Provides in-memory storage capabilities
- `MockSettings`: A mock implementation of settings with a proper `load()` method

### Adapter and Config Mocking

The test suite includes proper mocking for adapter implementations:

1. No actual files or directories are created during tests
2. No actual configuration files are read
3. All filesystem operations are properly mocked

### Mock Class Method Delegation

When creating mock classes for testing adapters, it's important to implement proper method delegation, especially when the class being mocked has both public and private methods. Follow these guidelines:

1. **Public-Private Method Delegation**: Ensure that public methods in mock classes properly delegate to their private counterparts, just as they do in the actual implementation.

   ```python
   # Original class
   class SomeAdapter:
       def public_method(self, arg):
           return self._private_method(arg)

       def _private_method(self, arg):
           # Implementation

   # Mock class - CORRECT implementation
   class MockAdapter:
       def public_method(self, arg):
           return self._private_method(arg)  # Proper delegation

       def _private_method(self, arg):
           # Mock implementation
   ```

2. **Separate Test Classes for Complex Mocks**: For adapters with complex dependencies, create separate test classes with their own fixtures.

3. **Patching External Dependencies**: Use `unittest.mock.patch` to mock external dependencies like file system operations.

4. **Exception Handling in Mocks**: Ensure that mock objects properly handle exceptions that would occur in the real implementation.

### Example: Proper Mock Implementation

```python
# Test class with proper method delegation
class TestTemplateRenderer:
    @pytest.fixture
    def template_renderer_mock(self):
        class MockTemplateRenderer:
            def __init__(self):
                self.templates = {}

            def render(self, template_name, context):
                # Public method delegates to private method
                return self._render(template_name, context)

            def _render(self, template_name, context):
                # Mock implementation
                return f"Rendered {template_name} with {context}"

        return MockTemplateRenderer()

    def test_template_renderer(self, template_renderer_mock):
        result = template_renderer_mock.render("test.html", {"key": "value"})
        assert "Rendered test.html" in result
        assert "{'key': 'value'}" in result
```

## Test Organization

For adapter tests, the project follows a structured approach:

1. **Base Test Files**: Each adapter category has base test files that contain:
   - Common test fixtures
   - Base class tests
   - Shared assertion utilities

2. **Implementation-Specific Tests**: Each adapter implementation has its own test file that:
   - Focuses on implementation-specific behavior
   - Uses fixtures and utilities from the base test file
   - Implements proper mock objects with method delegation

3. **Reusable Test Functions**: Where possible, test functions are designed to be reusable across different adapter implementations.

## Mocking the ACB Framework

FastBlocks relies on the [Asynchronous Component Base (ACB)](https://github.com/lesleslie/acb) framework, which requires special handling in tests to prevent filesystem access. The test suite includes comprehensive mocking of ACB components:

### Using MockAsyncPath

The `MockAsyncPath` class is a drop-in replacement for `anyio.Path` that avoids filesystem access:

```python
class MockAsyncPath:
    def __init__(self, path: Union[str, Path, "MockAsyncPath"] = "") -> None:
        if isinstance(path, MockAsyncPath):
            self._path = path._path
        else:
            self._path = str(path)

    async def exists(self) -> bool:
        return True  # Always return True to avoid filesystem checks

    async def is_dir(self) -> bool:
        return not await self.is_file()

    async def is_file(self) -> bool:
        return "." in self._path.split("/")[-1]

    async def iterdir(self):
        # Return an async iterator with no items
        class AsyncIterator:
            def __init__(self, items=None):
                self.items = items or []
                self.index = 0

            def __aiter__(self):
                return self

            async def __anext__(self):
                if self.index >= len(self.items):
                    raise StopAsyncIteration
                item = self.items[self.index]
                self.index += 1
                return item

        return AsyncIterator()
```

This implementation allows tests to mock filesystem operations without actually accessing the filesystem.

### Mocking ACB Register Functions

Two critical ACB functions that attempt filesystem access are `register_pkg()` and `register_actions()`. The test suite includes a utility script `patch_site_packages.py` that can patch these functions in the installed ACB package:

```python
# Example usage of patch_site_packages.py
python tests/patch_site_packages.py --verbose  # Apply the patches
# Run your tests...
python tests/patch_site_packages.py --restore  # Restore original files
```

The patched versions of these functions are no-ops that avoid filesystem access:

```python
# Patched register_pkg
def register_pkg() -> None:
    # Patched by FastBlocks tests
    return

# Patched register_actions
async def register_actions(path: AsyncPath) -> list[Action]:
    # Patched by FastBlocks tests
    return []
```

### Mocking ACB Modules in conftest.py

The test suite's `conftest.py` includes comprehensive mocking of ACB modules:

```python
def _patch_acb_modules() -> None:
    """Patch ACB modules to prevent filesystem access during tests."""
    # Create mock modules
    mock_acb_module = types.ModuleType('acb')
    mock_acb_module.__path__ = ['/mock/path/to/acb']

    mock_acb_config = types.ModuleType('acb.config')
    mock_acb_depends = types.ModuleType('acb.depends')
    mock_acb_actions = types.ModuleType('acb.actions')
    mock_acb_adapters = types.ModuleType('acb.adapters')

    # Add to sys.modules
    sys.modules['acb'] = mock_acb_module
    sys.modules['acb.config'] = mock_acb_config
    sys.modules['acb.depends'] = mock_acb_depends
    sys.modules['acb.actions'] = mock_acb_actions
    sys.modules['acb.adapters'] = mock_acb_adapters

    # Set up mock implementations
    # ... (see conftest.py for complete implementation)
```

## Test Isolation Techniques

To ensure tests run independently and don't interfere with each other, the test suite employs several isolation techniques:

1. **Module Patching**: System modules are patched at the beginning of each test session to prevent real imports from accessing the filesystem.

2. **Fixture Isolation**: Test fixtures are designed to be isolated, with each test receiving its own instance of mock objects.

3. **Context Managers**: Context managers are used to ensure that patches are properly applied and removed, even if tests fail.

4. **Mock Implementations**: Complete mock implementations of FastBlocks and ACB components prevent any actual configuration loading or filesystem access.

5. **Stateless Tests**: Tests are designed to be stateless, not relying on global state that could be modified by other tests.

Example of module isolation in a test file:

```python
@pytest.fixture(autouse=True)
def clean_modules() -> t.Generator[None]:
    """Save original modules and restore after test."""
    original_modules = sys.modules.copy()

    for mod in list(sys.modules.keys()):
        if mod.startswith(("fastblocks", "acb", "typer", "uvicorn", "granian")):
            sys.modules.pop(mod, None)

    yield

    sys.modules.clear()
    sys.modules.update(original_modules)
```

## Test Coverage

The current test coverage is approximately 34% overall, with particularly good coverage in the templates adapter code (79% for `_base.py`). All 155 tests pass successfully without requiring filesystem access.

## Testing with Crackerjack

[Crackerjack](https://github.com/lesleslie/crackerjack) is a tool that can be used to run tests with AI assistance. It's particularly useful for debugging failing tests and understanding test behavior.

### Basic Usage

To run tests with Crackerjack:

```bash
python -m crackerjack
```

Or if using PDM:

```bash
pdm run python -m crackerjack
```

### Using the AI Agent

The `--ai-agent` flag enables AI assistance when running tests:

```bash
python -m crackerjack --ai-agent
```

This will provide AI-powered analysis of test failures and suggestions for fixes.

### Showing Output with -s Flag

When running tests with Crackerjack, you can use the `-s` flag to show print statements and other output during test execution:

```bash
python -m crackerjack -s
```

You can combine this with the AI agent flag:

```bash
python -m crackerjack --ai-agent -s
```

### Running Specific Tests

Crackerjack accepts command line arguments for specific options, but doesn't directly accept test file paths like pytest does. Instead, it's typically run with specific flags for its automated workflow:

```bash
# Run with AI agent assistance
python -m crackerjack --ai-agent

# Show output during test execution
python -m crackerjack -s

# Run the full automated workflow (linting, testing, version bump, commit)
python -m crackerjack -x -t -p <version> -c

# Alternative automated workflow
python -m crackerjack -a <version>
```

To run specific tests, you should use pytest directly:

```bash
# Run tests in a specific directory
pytest tests/adapters/templates/

# Run a specific test file with output shown
pytest tests/adapters/templates/test_templates.py -s
```

### Benefits of Using Crackerjack

1. **AI-Assisted Debugging**: The AI agent can analyze test failures and suggest fixes
2. **Detailed Output**: Using the `-s` flag provides visibility into what's happening during test execution
3. **Compatible with FastBlocks' Test Suite**: The test suite has been configured to work properly with Crackerjack

## Troubleshooting Common Test Issues

### Missing Mock Implementation

If you encounter errors related to missing mock implementations, you may need to extend the mocking framework to support additional functionality.

### Test Isolation Issues

If tests fail inconsistently, check for shared state between tests that could cause interference.

### Slow Tests

Tests that run slowly might be accessing external resources or the filesystem. Ensure they're properly using the mocking framework.

### ACB-Related Test Failures

ACB-related test failures are often caused by the framework attempting to access the filesystem. Here are common issues and solutions:

#### FileNotFoundError for settings files

If you see errors like:
```
FileNotFoundError: [Errno 2] No such file or directory: '/path/to/settings/debug.yml'
```

This usually means that ACB is trying to load actual configuration files. Solutions:

1. **Patch the ACB register_pkg function**:
   ```bash
   python tests/patch_site_packages.py
   ```

2. **Mock Config class**: Ensure tests use the `MockConfig` class instead of the real `Config` class.

3. **Mock settings loading**: Add explicit patches for settings loading functions.

#### AsyncPath iterdir() issues

Errors involving `iterdir()` or async iteration often look like:
```
TypeError: 'async for' requires an object with __aiter__ method, got coroutine
```

This happens when `MockAsyncPath.iterdir()` doesn't properly implement the async iterator protocol. Solution:

1. Ensure your `MockAsyncPath` class properly implements the async iterator protocol as shown in the example above.

2. Make sure `iterdir()` returns an object with both `__aiter__` and `__anext__` methods.

#### ACB module import errors

If you see errors like:
```
ModuleNotFoundError: No module named 'acb.actions.encode'
```

The test is trying to import a real ACB module. Solutions:

1. **Add comprehensive module mocking**: Make sure all ACB modules are mocked in `conftest.py`.

2. **Patch imports at the module level**: In specific test files, add module-level patches:
   ```python
   # At the top of your test file
   import sys
   import types
   from unittest.mock import MagicMock

   # Create and patch ACB modules before other imports
   mock_acb = types.ModuleType('acb')
   mock_acb.register_pkg = MagicMock()
   sys.modules['acb'] = mock_acb
   # ... additional module patching
   ```

3. **Use the ensure_cli_module fixture**: For CLI tests, use the `ensure_cli_module` fixture which provides comprehensive mocking of the CLI's dependencies.
