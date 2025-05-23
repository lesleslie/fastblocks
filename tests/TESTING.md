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
