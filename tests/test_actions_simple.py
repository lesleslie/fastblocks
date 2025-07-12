"""Simple actions tests."""

from fastblocks.actions.minify import minify


def test_minify_js() -> None:
    """Test minify.js method."""
    js_content = "function test() { return 'hello'; }"
    result = minify.js(js_content)
    assert isinstance(result, str | bytes | bytearray)
    assert result


def test_minify_js_empty() -> None:
    """Test minify.js with empty string."""
    result = minify.js("")
    assert result == ""


def test_minify_js_whitespace() -> None:
    """Test minify.js with whitespace."""
    result = minify.js("   \n\t  ")
    assert result == ""


def test_minify_html() -> None:
    """Test minify.html method."""
    html_content = "<html><body>  Hello World  </body></html>"
    result = minify.html(html_content)
    assert isinstance(result, str)
    assert result
    assert len(result) <= len(html_content)


def test_minify_html_empty() -> None:
    """Test minify.html with empty string."""
    result = minify.html("")
    assert result == ""


def test_minify_html_whitespace() -> None:
    """Test minify.html with whitespace."""
    result = minify.html("   \n\t  ")
    assert result == ""


def test_minify_css() -> None:
    """Test minify.css method."""
    css_content = "body { color: red; background: blue; }"
    result = minify.css(css_content)
    assert isinstance(result, str | bytes | bytearray)
    assert result


def test_minify_css_empty() -> None:
    """Test minify.css with empty string."""
    result = minify.css("")
    assert result == ""


def test_minify_css_whitespace() -> None:
    """Test minify.css with whitespace."""
    result = minify.css("   \n\t  ")
    assert result == ""


def test_minify_css_media_query() -> None:
    """Test minify.css with media query."""
    css_content = "@media (max-width: 600px) { body { font-size: 14px; } }"
    result = minify.css(css_content)
    assert isinstance(result, str | bytes | bytearray)
    assert result
    # Check that the media query transformation happened
    assert "@media(" in str(result)


def test_minify_object_methods() -> None:
    """Test that minify object has expected methods."""
    assert hasattr(minify, "js")
    assert hasattr(minify, "html")
    assert hasattr(minify, "css")
    assert callable(minify.js)
    assert callable(minify.html)
    assert callable(minify.css)
