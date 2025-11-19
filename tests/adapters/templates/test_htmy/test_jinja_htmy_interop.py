#!/usr/bin/env python3
"""Test Jinja2-HTMY interoperability."""

import asyncio
import os
import sys
import typing as t
from unittest.mock import Mock

import pytest

# Add the current directory to sys.path
sys.path.insert(0, "/Users/les/Projects/sites/fastest")
sys.path.insert(0, "/Users/les/Projects/fastblocks")
sys.path.insert(0, "/Users/les/Projects/acb")

# Disable ACB library mode
os.environ["ACB_LIBRARY_MODE"] = "false"


@pytest.mark.integration
async def test_jinja_htmy_interop() -> None:
    """Test HTMY component rendering within Jinja2 templates."""
    print("=== Jinja2-HTMY Interoperability Test ===")

    try:
        templates, mock_request = await _setup_jinja_test_environment()
        context = _create_test_context()

        await _test_template_rendering(templates, mock_request, context)
        await _test_direct_component_rendering(templates, mock_request)

    except Exception as e:
        print(f"✗ Error: {e}")
        import traceback

        traceback.print_exc()


async def _setup_jinja_test_environment() -> tuple[t.Any, Mock]:
    """Set up the test environment for Jinja2-HTMY integration."""
    from acb import register_pkg

    register_pkg()

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
    mock_request.url.path = "/test"
    mock_request.method = "GET"

    return templates, mock_request


def _create_test_context() -> dict[str, str]:
    """Create test context data."""
    return {
        "username": "John Doe",
        "user_email": "john.doe@example.com",
        "page_title": "Interop Test",
    }


async def _test_template_rendering(
    templates: t.Any, mock_request: Mock, context: dict[str, t.Any]
) -> None:
    """Test Jinja2 template rendering with HTMY components."""
    print("\\n=== Testing Jinja2 Template with HTMY Components ===")

    response = await templates.render_template(
        request=mock_request, template="test_jinja_htmy.html", context=context
    )

    print("✓ Template rendered successfully!")
    print(f"  Response type: {type(response)}")
    print(f"  Status code: {getattr(response, 'status_code', 'N/A')}")

    content = _extract_response_content(response)
    print(f"  Content length: {len(content)}")

    _validate_template_content(content)


def _extract_response_content(response: t.Any) -> str:
    """Extract content from response object."""
    if hasattr(response, "body"):
        return (
            response.body.decode()
            if isinstance(response.body, bytes)
            else str(response.body)
        )
    elif hasattr(response, "content"):
        return (
            response.content.decode()
            if isinstance(response.content, bytes)
            else str(response.content)
        )
    return str(response)


def _validate_template_content(content: str) -> None:
    """Validate the rendered template content."""
    checks = [
        ("Jinja2 title", "HTMY-Jinja2 Interoperability Test" in content),
        ("Jinja2 context", "John Doe" in content),
        ("HTMY component marker", "HTMY Component Rendered Successfully!" in content),
        ("Component with params", "Alice Johnson" in content),
        (
            "Basic render_component call",
            "render_component" not in content or "<!-- Error" in content,
        ),
    ]

    print("\\n=== Content Validation ===")
    all_passed = True
    for check_name, check_result in checks:
        status = "✓" if check_result else "❌"
        print(f"  {status} {check_name}: {check_result}")
        if not check_result:
            all_passed = False

    _report_validation_results(all_passed, content)


def _report_validation_results(all_passed: bool, content: str) -> None:
    """Report validation results."""
    if all_passed:
        print("\\n🎉 Jinja2-HTMY interoperability is working!")
    else:
        print("\\n⚠️  Some checks failed - see content below:")
        print("\\n=== Full Content ===")
        print(content[:1000] + ("..." if len(content) > 1000 else ""))


async def _test_direct_component_rendering(
    templates: t.Any, mock_request: Mock
) -> None:
    """Test direct component rendering for comparison."""
    print("\\n=== Testing Direct Component Rendering ===")

    direct_response = await templates.render_component(
        request=mock_request,
        component="user_card",
        name="Direct Test User",
        email="direct@example.com",
    )

    direct_content = _extract_response_content(direct_response)

    print("✓ Direct component rendering:")
    print(f"  Content: {direct_content[:200]}...")

    if "HTMY Component Rendered Successfully!" in direct_content:
        print("✓ Direct HTMY component rendering works")
    else:
        print("❌ Direct HTMY component rendering failed")


if __name__ == "__main__":
    asyncio.run(test_jinja_htmy_interop())
