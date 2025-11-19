#!/usr/bin/env python3
"""Test basic HTMY component rendering."""

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
async def test_htmy_component() -> None:
    print("=== HTMY Component Test ===")

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

        # Try to render the user_card component
        print("\n=== Testing Component Rendering ===")

        response = await templates.render_component(
            request=mock_request,
            component="user_card",
            context={},
            name="John Doe",
            email="john@example.com",
        )

        print("✓ Component rendered successfully!")
        print(f"  Response type: {type(response)}")
        print(f"  Status code: {getattr(response, 'status_code', 'N/A')}")

        # Check if it has content
        if hasattr(response, "body"):
            content = (
                response.body.decode()
                if isinstance(response.body, bytes)
                else str(response.body)
            )
        elif hasattr(response, "content"):
            content = (
                response.content.decode()
                if isinstance(response.content, bytes)
                else str(response.content)
            )
        else:
            content = str(response)

        print(f"  Content length: {len(content)}")
        print(f"  Content preview: {content[:200]}...")

        if "HTMY Component Rendered Successfully!" in content:
            print("🎉 HTMY component rendering is working!")
        else:
            print("❌ HTMY component content not found")

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_htmy_component())
