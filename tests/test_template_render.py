#!/usr/bin/env python3
"""Test template rendering end-to-end."""

import asyncio
import os
import sys

import pytest

# Add the current directory to sys.path
sys.path.insert(0, "/Users/les/Projects/sites/fastest")
sys.path.insert(0, "/Users/les/Projects/fastblocks")
sys.path.insert(0, "/Users/les/Projects/acb")

# Disable ACB library mode
os.environ["ACB_LIBRARY_MODE"] = "false"


@pytest.mark.unit
async def test_template_render() -> None:
    print("=== Template Rendering Test ===")

    try:
        from acb import register_pkg

        register_pkg()

        from unittest.mock import Mock

        from acb.config import Config
        from acb.depends import depends
        from fastblocks.adapters.templates.jinja2 import Templates

        # Initialize config
        config = Config()
        depends.set("config", config)
        config.init()

        print("✓ Config initialized")

        # Initialize templates
        templates = Templates()
        await templates.init()

        print("✓ Templates initialized")

        # Create a mock request
        mock_request = Mock()
        mock_request.url.path = "/"
        mock_request.method = "GET"

        # Try to render the template
        response = await templates.render_template(
            request=mock_request, template="index.html", context={"title": "Test"}
        )

        print("✓ Template rendered successfully!")
        print(f"  Response type: {type(response)}")
        print(f"  Status code: {getattr(response, 'status_code', 'N/A')}")

        # Check if it has content
        if hasattr(response, "body"):
            print(f"  Content length: {len(response.body)}")
        elif hasattr(response, "content"):
            print(f"  Content length: {len(response.content)}")
        else:
            print("  Content: Not found")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_template_render())
