#!/usr/bin/env python3
"""Test FileSystemLoader directly."""

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

from anyio import Path as AsyncPath
from fastblocks.adapters.templates.jinja2 import FileSystemLoader


@pytest.mark.unit
async def test_filesystem_loader() -> None:
    print("=== FileSystemLoader Test ===")

    # Create search paths that match what we saw in the debug output
    search_paths = [
        AsyncPath("/Users/les/Projects/sites/fastest/templates/app/bulma/app/theme"),
        AsyncPath("/Users/les/Projects/sites/fastest/templates/app/bulma/app"),
        AsyncPath("/Users/les/Projects/sites/fastest/templates/app/bulma"),
        AsyncPath("/Users/les/Projects/sites/fastest/templates/app/base"),
    ]

    print("Search paths:")
    for i, path in enumerate(search_paths):
        exists = await path.exists()
        print(f"  {i}: {path} (exists: {exists})")
        if exists:
            index_path = path / "index.html"
            index_exists = await index_path.exists()
            print(f"      index.html exists: {index_exists}")

    # Test the loader
    print("\n=== Testing FileSystemLoader ===")

    loader = FileSystemLoader(search_paths)
    print(f"Loader searchpath: {loader.searchpath}")

    try:
        result = await loader.get_source_async("index.html")
        print("✓ Successfully loaded template!")
        print(f"  Source length: {len(result[0])}")
        print(f"  Template name: {result[1]}")
    except Exception as e:
        print(f"✗ Failed to load template: {e}")
        import traceback

        traceback.print_exc()

        # Try to debug further
        print("\n=== Debugging FileSystemLoader ===")
        try:
            # Test the _find_template_path_parallel method
            template_path = await loader._find_template_path_parallel("index.html")
            print(f"Found template path: {template_path}")

            if template_path:
                exists = await template_path.exists()
                print(f"Template path exists: {exists}")

                if exists:
                    content = await template_path.read_bytes()
                    print(f"Template content length: {len(content)}")

        except Exception as debug_error:
            print(f"Debug error: {debug_error}")
            traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_filesystem_loader())
