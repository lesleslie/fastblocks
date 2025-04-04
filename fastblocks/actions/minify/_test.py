from fastblocks.actions.minify import minify


class TestMinify:
    def test_js_minification(self) -> None:
        js_content: str = (
            "// This is a comment"
            "function greet(name) {"
            "// This is another comment"
            "    console.log('Hello, ' + name + '!');"
            "    "
            "    return true;"
            "}"
        )

        minified_js: str | bytes | bytearray = minify.js(js_content)
        minified_js_str = (
            str(minified_js)
            if isinstance(minified_js, (bytes, bytearray))
            else minified_js
        )

        assert "// This is a comment" not in minified_js_str
        assert "// This is another comment" not in minified_js_str
        assert "\n" not in minified_js_str

        assert "function greet(name)" in minified_js_str
        assert "console.log('Hello,'+name+'!')" in minified_js_str
        assert "return true" in minified_js_str

    def test_html_minification(self) -> None:
        html_content: str = (
            "<!DOCTYPE html>"
            "<html>"
            "<head>"
            "    <title>Test Page</title>"
            "    <!-- This is a comment -->"
            "    <style>"
            "        body {"
            "            font-family: Arial, sans-serif;"
            "            margin: 0;"
            "            padding: 20px;"
            "        }"
            "    </style>"
            "</head>"
            "<body>"
            "   <h1>Hello, World!</h1>"
            "   "
            "   <div class='container'>"
            "       <p>This is a test paragraph.</p>"
            "    </div>"
            "</body>"
            "</html>"
            "    <div class='container'>"
            "        <p>This is a test paragraph.</p>"
            "    </div>"
            "   "
            "    <script>"
            "        // JavaScript comment"
            "        console.log('Hello!');"
            "    </script>"
            "</body>"
            "</html>"
        )

        minified_html: str = minify.html(html_content)

        assert "<!-- This is a comment -->" not in minified_html
        assert "// JavaScript comment" not in minified_html

        assert "<!DOCTYPE html>" in minified_html
        assert "<html>" in minified_html
        assert "<head>" in minified_html
        assert "<title>Test Page</title>" in minified_html
        assert "<body>" in minified_html
        assert "<h1>Hello, World!</h1>" in minified_html
        assert '<div class="container">' in minified_html
        assert "<p>This is a test paragraph.</p>" in minified_html

    def test_css_minification(self) -> None:
        css_content: str = (
            "/* Main styles */"
            "body {"
            "    font-family: Arial, sans-serif;"
            "    color: #333;"  # skip
            "    margin: 0;"
            "    padding: 20px;"
            "}"
            "   "
            "/* Container styles */"
            ".container {"
            "    max-width: 1200px;"
            "   margin: 0 auto;"
            "    padding: 15px;"
            "}"
            "   "
            "/* Header styles */"
            "h1, h2, h3 {"
            "    color: #007bff;"  # skip
            "    margin-bottom: 15px;"
            "}"
        )

        minified_css: str | bytes | bytearray = minify.css(css_content)
        minified_css_str = (
            str(minified_css)
            if isinstance(minified_css, (bytes, bytearray))
            else minified_css
        )

        assert "/* Main styles */" not in minified_css_str
        assert "/* Container styles */" not in minified_css_str
        assert "/* Header styles */" not in minified_css_str

        assert "body{" in minified_css_str
        assert "font-family:Arial,sans-serif" in minified_css_str
        assert "color:#333" in minified_css_str
        assert ".container{" in minified_css_str
        assert "max-width:1200px" in minified_css_str
        assert "h1,h2,h3{" in minified_css_str
        assert "color:#007bff" in minified_css_str

    def test_scss_minification(self) -> None:
        scss_content: str = (
            "/* Variables */\n"
            "$primary-color: #007bff;\n"
            "$secondary-color: #6c757d;\n"
            "$font-stack: Arial, sans-serif;\n"
            "\n"
            "/* Main styles */\n"
            "body {\n"
            "    font-family: $font-stack;\n"
            "    color: #333;\n"
            "    margin: 0;\n"
            "    padding: 20px;\n"
            "\n"
            "    // Nested rule\n"
            "    .container {\n"
            "        max-width: 1200px;\n"
            "        margin: 0 auto;\n"
            "        padding: 15px;\n"
            "\n"
            "        h1 {\n"
            "            color: $primary-color;\n"
            "            margin-bottom: 15px;\n"
            "        }\n"
            "    }\n"
            "}\n"
            "\n"
            "/* Mixins */\n"
            "@mixin button-style($bg-color) {\n"
            "    background-color: $bg-color;\n"
            "    color: white;\n"
            "    padding: 10px 15px;\n"
            "    border: none;\n"
            "    border-radius: 4px;\n"
            "}\n"
            "\n"
            ".button-primary {\n"
            "    @include button-style($primary-color);\n"
            "}\n"
            "\n"
            ".button-secondary {\n"
            "    @include button-style($secondary-color);\n"
            "}"
        )

        minified_scss: str | bytes | bytearray = minify.css(scss_content)
        minified_scss_str = (
            str(minified_scss)
            if isinstance(minified_scss, (bytes, bytearray))
            else minified_scss
        )

        assert "/* Variables */" not in minified_scss_str
        assert "/* Main styles */" not in minified_scss_str
        assert "/* Mixins */" not in minified_scss_str

        assert "$primary-color:#007bff" in minified_scss_str
        assert "$secondary-color:#6c757d" in minified_scss_str
        assert "$font-stack:Arial,sans-serif" in minified_scss_str
        assert "font-family:$font-stack" in minified_scss_str
        assert ".container{" in minified_scss_str
        assert "h1{" in minified_scss_str
        assert "color:$primary-color" in minified_scss_str
        assert "@mixin button-style($bg-color){" in minified_scss_str
        assert "background-color:$bg-color" in minified_scss_str
        assert "@include button-style($primary-color)" in minified_scss_str
        assert "@include button-style($secondary-color)" in minified_scss_str

    def test_js_minification_with_empty_input(self) -> None:
        result1 = minify.js("")
        result2 = minify.js("   ")
        result1_str = (
            str(result1) if isinstance(result1, (bytes, bytearray)) else result1
        )
        result2_str = (
            str(result2) if isinstance(result2, (bytes, bytearray)) else result2
        )
        assert result1_str == "" or not result1_str
        assert result2_str == "" or not result2_str

    def test_html_minification_with_empty_input(self) -> None:
        assert minify.html("") == ""
        assert minify.html("   ") == ""

    def test_css_minification_with_empty_input(self) -> None:
        result1 = minify.css("")
        result2 = minify.css("   ")
        result1_str = (
            str(result1) if isinstance(result1, (bytes, bytearray)) else result1
        )
        result2_str = (
            str(result2) if isinstance(result2, (bytes, bytearray)) else result2
        )
        assert result1_str == "" or not result1_str
        assert result2_str == "" or not result2_str

    def test_scss_minification_with_empty_input(self) -> None:
        result1 = minify.css("")
        result2 = minify.css("   ")
        result1_str = (
            str(result1) if isinstance(result1, (bytes, bytearray)) else result1
        )
        result2_str = (
            str(result2) if isinstance(result2, (bytes, bytearray)) else result2
        )
        assert result1_str == "" or not result1_str
        assert result2_str == "" or not result2_str

    def test_js_minification_preserves_functionality(self) -> None:
        js_content: str = (
            "function calculateSum(a, b) {\n"
            "    return a + b;\n"
            "}\n"
            "\n"
            "const multiply = (a, b) => {\n"
            "    return a * b;\n"
            "};\n"
            "\n"
            "class Calculator {\n"
            "    constructor() {\n"
            "        this.value = 0;\n"
            "    }\n"
            "\n"
            "    add(num) {\n"
            "        this.value += num;\n"
            "        return this;\n"
            "    }\n"
            "\n"
            "    subtract(num) {\n"
            "        this.value -= num;\n"
            "        return this;\n"
            "    }\n"
            "\n"
            "    getValue() {\n"
            "        return this.value;\n"
            "    }\n"
            "}"
        )

        minified_js: str | bytes | bytearray = minify.js(js_content)
        minified_js_str = (
            str(minified_js)
            if isinstance(minified_js, (bytes, bytearray))
            else minified_js
        )

        assert "function calculateSum(a,b)" in minified_js_str
        assert "return a+b" in minified_js_str
        assert "const multiply=(a,b)=>" in minified_js_str
        assert "return a*b" in minified_js_str
        assert "class Calculator{" in minified_js_str
        assert "constructor(){" in minified_js_str
        assert "this.value=0" in minified_js_str
        assert "add(num){" in minified_js_str
        assert "this.value+=num" in minified_js_str
        assert "return this" in minified_js_str
        assert "subtract(num){" in minified_js_str
        assert "this.value-=num" in minified_js_str
        assert "getValue(){" in minified_js_str
        assert "return this.value" in minified_js_str

    def test_html_minification_with_attributes(self) -> None:
        html_content: str = (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n'
            "<head>\n"
            '    <meta charset="UTF-8">\n'
            '    <meta name="viewport" content="width=device-width, initial-scale=1.0">\n'
            "    <title>Test Page</title>\n"
            "</head>\n"
            "<body>\n"
            '    <div id="main" class="container" data-test="value">\n'
            '        <a href="https://example.com" target="_blank" rel="noopener">Link</a>\n'
            '        <img src="image.jpg" alt="Test image" width="100" height="100">\n'
            '        <form action="/submit" method="post">\n'
            '            <input type="text" name="username" placeholder="Username" required>\n'
            '            <input type="password" name="password" placeholder="Password" required>\n'
            '            <button type="submit">Submit</button>\n'
            "        </form>\n"
            "    </div>\n"
            "</body>\n"
            "</html>"
        )

        minified_html: str = minify.html(html_content)

        assert 'lang="en"' in minified_html
        assert 'charset="UTF-8"' in minified_html
        assert 'name="viewport"' in minified_html
        assert 'content="width=device-width,initial-scale=1.0"' in minified_html
        assert 'id="main"' in minified_html
        assert 'class="container"' in minified_html
        assert 'data-test="value"' in minified_html
        assert 'href="https://example.com"' in minified_html
        assert 'target="_blank"' in minified_html
        assert 'rel="noopener"' in minified_html
        assert 'src="image.jpg"' in minified_html
        assert 'alt="Test image"' in minified_html
        assert 'width="100"' in minified_html
        assert 'height="100"' in minified_html
        assert 'action="/submit"' in minified_html
        assert 'method="post"' in minified_html
        assert 'type="text"' in minified_html
        assert 'name="username"' in minified_html
        assert 'placeholder="Username"' in minified_html
        assert "required" in minified_html
        assert 'type="password"' in minified_html
        assert 'name="password"' in minified_html
        assert 'placeholder="Password"' in minified_html
        assert 'type="submit"' in minified_html

    def test_css_minification_with_media_queries(self) -> None:
        css_content: str = (
            "body {\n"
            "    font-size: 16px;\n"
            "}\n"
            "\n"
            "@media (max-width: 768px) {\n"
            "    body {\n"
            "        font-size: 14px;\n"
            "    }\n"
            "\n"
            "    .container {\n"
            "        padding: 10px;\n"
            "    }\n"
            "}\n"
            "\n"
            "@media (max-width: 480px) {\n"
            "    body {\n"
            "        font-size: 12px;\n"
            "    }\n"
            "\n"
            "    .container {\n"
            "        padding: 5px;\n"
            "    }\n"
            "}"
        )

        minified_css: str | bytes | bytearray = minify.css(css_content)
        minified_css_str = (
            str(minified_css)
            if isinstance(minified_css, (bytes, bytearray))
            else minified_css
        )

        assert "body{font-size:16px}" in minified_css_str
        assert "@media(max-width:768px){" in minified_css_str
        assert "body{font-size:14px}" in minified_css_str
        assert ".container{padding:10px}" in minified_css_str
        assert "@media(max-width:480px){" in minified_css_str
        assert "body{font-size:12px}" in minified_css_str
        assert ".container{padding:5px}" in minified_css_str
