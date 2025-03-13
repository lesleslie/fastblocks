# FastBlocks Actions

> **FastBlocks Documentation**: [Main](../../README.md) | [Core Features](../README.md) | [Actions](./README.md) | [Adapters](../adapters/README.md)

Actions in FastBlocks are utility functions that perform specific tasks. They are designed to be reusable, self-contained, and easily accessible throughout your application.

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

- **HTML**: [minify-html](https://github.com/wilsonzlin/minify-html)
- **CSS**: [rcssmin](https://github.com/ndparker/rcssmin)
- **JavaScript**: [rjsmin](https://github.com/ndparker/rjsmin)

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
