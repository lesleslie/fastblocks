# FastBlocks Actions

> **FastBlocks Documentation**: [Main](../../README.md) | [Core Features](../README.md) | [Actions](./README.md) | [Adapters](../adapters/README.md)

Actions in FastBlocks are utility functions that perform specific tasks. They are designed to be reusable, self-contained, and easily accessible throughout your application.

## Relationship with ACB

FastBlocks actions build on [ACB's action system](https://github.com/lesleslie/acb/blob/main/acb/actions/README.md) but with a different focus:

- **ACB Actions**: Focus on general-purpose utilities like compression, encoding, and hashing
- **FastBlocks Actions**: Focus on web-specific utilities like HTML/CSS/JS minification

Both use the same pattern of self-contained, automatically discovered utility functions, but serve different purposes in the application stack.

## Available Actions

| Action | Description | Functions |
|--------|-------------|-----------|
| [Minify](#minify) | Minifies HTML, CSS, and JavaScript | `minify.html()`, `minify.css()`, `minify.js()` |

## Minify

The `minify` action provides functions to minify HTML, CSS, and JavaScript content, reducing file size and improving load times.

### Usage

```python
from fastblocks.actions.minify import minify

# Minify HTML content
html_content = """
<!DOCTYPE html>
<html>
<head>
    <title>Example</title>
</head>
<body>
    <h1>Hello, World!</h1>
</body>
</html>
"""
minified_html = minify.html(html_content)

# Minify CSS content
css_content = """
body {
    font-family: Arial, sans-serif;
    color: #333;
    margin: 0;
    padding: 20px;
}
"""
minified_css = minify.css(css_content)

# Minify JavaScript content
js_content = """
function greet(name) {
    console.log('Hello, ' + name + '!');
}
"""
minified_js = minify.js(js_content)
```

### API Reference

#### `minify.html(html: str) -> str`

Minifies HTML content by removing unnecessary whitespace, comments, and optimizing markup.

- **Parameters**:
  - `html` (str): The HTML content to minify
- **Returns**:
  - `str`: The minified HTML content

#### `minify.css(css: str) -> str`

Minifies CSS content by removing whitespace, comments, and optimizing style rules.

- **Parameters**:
  - `css` (str): The CSS content to minify
- **Returns**:
  - `str`: The minified CSS content

#### `minify.js(js: str) -> str`

Minifies JavaScript content by removing whitespace, comments, and optimizing code.

- **Parameters**:
  - `js` (str): The JavaScript content to minify
- **Returns**:
  - `str`: The minified JavaScript content

### Implementation Details

The minify action uses the following libraries:

- **HTML**: [minify-html](https://github.com/wilsonzlin/minify-html) (compatible with v0.16.4+)
- **CSS**: [rcssmin](https://github.com/ndparker/rcssmin) (compatible with v1.2.1+)
- **JavaScript**: [rjsmin](https://github.com/ndparker/rjsmin) (compatible with v1.2.4+)

These dependencies are automatically installed when you install FastBlocks with the required extras:

```bash
pdm add "fastblocks[minify]"
# or
pip install "fastblocks[minify]"
```

## Creating Custom Actions

You can create your own actions by adding Python modules to the `actions` directory:

```python
# fastblocks/actions/validate.py
class Validate:
    @staticmethod
    def email(email: str) -> bool:
        """Validate an email address"""
        import re
        pattern = r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
        return bool(re.match(pattern, email))

validate = Validate()
```

Then you can use your custom action in your application:

```python
from fastblocks.actions.validate import validate

is_valid = validate.email("user@example.com")
```

### Best Practices for Custom Actions

1. **Keep actions focused**: Each action should perform a specific, well-defined task
2. **Make actions stateless**: Actions should not maintain state between calls
3. **Use descriptive names**: Action names should clearly indicate their purpose
4. **Document your actions**: Include docstrings and type hints
5. **Add tests**: Ensure your actions work correctly with unit tests

### Testing Custom Actions

To create tests for your custom actions, add test files to the `tests/actions/` directory:

```python
# tests/actions/validate/test_validate.py
import pytest
from fastblocks.actions.validate import validate

def test_email_validation_valid():
    """Test that valid email addresses pass validation."""
    valid_emails = [
        "user@example.com",
        "firstname.lastname@example.com",
        "email@subdomain.example.com",
        "user+tag@example.com"
    ]
    for email in valid_emails:
        assert validate.email(email) is True

def test_email_validation_invalid():
    """Test that invalid email addresses fail validation."""
    invalid_emails = [
        "plainaddress",
        "@missingusername.com",
        "user@.com",
        "user@domain"
    ]
    for email in invalid_emails:
        assert validate.email(email) is False
```

Run your tests with pytest:

```bash
python -m pytest tests/actions/validate/test_validate.py -v
```

For more information on testing, see the [Testing Documentation](../../../tests/TESTING.md).
