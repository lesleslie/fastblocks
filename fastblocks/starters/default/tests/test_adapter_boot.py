"""Adapter-boot tests — verifies the scaffold adapters can be imported
without raising. Auth and admin adapters MUST NOT bind routes.

# req: REQ-P2-B1-001, REQ-P2-B1-002, REQ-P2-B1-003, REQ-P2-B1-004
"""
from __future__ import annotations


def test_templates_adapter_imports() -> None:
    """Templates adapter module imports cleanly."""
    from adapters import templates

    assert hasattr(templates, "build")


def test_icons_adapter_imports() -> None:
    """Icons adapter module imports cleanly."""
    from adapters import icons

    assert hasattr(icons, "build")


def test_fonts_adapter_imports() -> None:
    """Fonts adapter module imports cleanly."""
    from adapters import fonts

    assert hasattr(fonts, "build")


def test_style_adapter_imports() -> None:
    """Style adapter module imports cleanly."""
    from adapters import style

    assert hasattr(style, "build")


def test_auth_adapter_does_not_bind_routes(client) -> None:
    """REQ-P2-B1-004: skeleton auth adapter exposes no URL surface."""
    for protected_path in ("/login", "/logout", "/auth", "/signup"):
        response = client.get(protected_path)
        assert response.status_code == 404, (
            f"Skeleton auth adapter must not bind {protected_path!r}, "
            f"but it returned {response.status_code}."
        )


def test_admin_adapter_does_not_bind_routes(client) -> None:
    """REQ-P2-B1-004: skeleton admin adapter exposes no URL surface."""
    for admin_path in ("/admin", "/admin/login", "/admin/users"):
        response = client.get(admin_path)
        assert response.status_code == 404, (
            f"Skeleton admin adapter must not bind {admin_path!r}, "
            f"but it returned {response.status_code}."
        )


def test_no_acb_imports_in_source() -> None:
    """REQ-P2-B1-003: no acb imports anywhere in the scaffold.

    Uses a regex matched at line start to allow comments and docstrings
    (including this test's own assertion messages) to mention the forbidden
    token without triggering a false positive.
    """
    import re
    from pathlib import Path

    pattern = re.compile(r"(?m)^\s*(?:import acb\b|from acb\b)")
    for py in Path(__file__).parent.parent.rglob("*.py"):
        # Skip this test file (its assertion text contains the literal tokens).
        if py.resolve() == Path(__file__).resolve():
            continue
        text = py.read_text()
        match = pattern.search(text)
        assert not match, f"forbidden acb import in {py}: {match.group(0)!r}"


def test_default_style_is_fastblocks_ui() -> None:
    """REQ-P2-B1-001: default style in app.yaml is fastblocks_ui, not vanilla."""
    from pathlib import Path

    text = (Path(__file__).parent.parent / "settings" / "app.yaml").read_text()
    assert "fastblocks_ui" in text
