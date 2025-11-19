#!/usr/bin/env python3
"""Test storage exists check."""

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
async def test_storage_check() -> None:
    print("=== Testing Storage Check ===")

    try:
        from acb import register_pkg

        register_pkg()

        from anyio import Path as AsyncPath
        from fastblocks.adapters.templates.jinja2 import FileSystemLoader, Templates

        # Create search paths
        search_paths = [
            AsyncPath("/Users/les/Projects/sites/fastest/templates/app/bulma"),
        ]

        loader = FileSystemLoader(search_paths)

        # Test the specific template
        template_path = search_paths[0] / "index.html"
        print(f"Template path: {template_path}")
        print(f"Template exists: {await template_path.exists()}")

        # Test storage path calculation
        storage_path = Templates.get_storage_path(template_path)
        print(f"Storage path: {storage_path}")

        # Test storage check
        storage_exists = await loader._check_storage_exists(storage_path)
        print(f"Storage exists: {storage_exists}")

        # Test the conditions
        fs_exists = await template_path.exists()
        deployed = getattr(loader.config, "deployed", True)
        print(f"fs_exists: {fs_exists}")
        print(f"deployed: {deployed}")
        print(f"Will sync: {storage_exists and fs_exists and (not deployed)}")

    except Exception as e:
        print(f"Error: {e}")
        import traceback

        traceback.print_exc()


if __name__ == "__main__":
    asyncio.run(test_storage_check())
