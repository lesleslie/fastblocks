"""Adapter-boot tests — verifies the hybrid templates adapter resolves
    through Oneiric and the HTMY component is constructible.

# req: REQ-P2-B3-001
"""
from __future__ import annotations


def test_templates_adapter_module_imports() -> None:
    """The local templates adapter module imports cleanly."""
    from adapters import templates

    assert hasattr(templates, "build")
    assert callable(templates.build)


def test_hybrid_adapter_resolves_through_oneiric() -> None:
    """``Resolver.resolve(domain="fastblocks", key="hybrid")`` returns the HybridTemplatesManager class."""
    from fastblocks.adapters.templates.hybrid import HybridTemplatesManager
    from fastblocks.core.resolver import get_resolver

    resolver = get_resolver()
    candidate = resolver.resolve("fastblocks", "hybrid")
    assert candidate is not None, "hybrid templates adapter not registered"
    factory = candidate.factory
    assert callable(factory), "hybrid candidate factory must be callable"
    instance = factory()
    assert isinstance(instance, HybridTemplatesManager)


def test_greeting_card_component_renders() -> None:
    """The HTMY GreetingCard renders to a greeting-card div."""
    import asyncio

    from htmy import Renderer

    from components.greeting_card import GreetingCardProps, greeting_card

    props = GreetingCardProps(
        name="Ada Lovelace",
        avatar="/static/ada.png",
        bio="First programmer.",
    )
    body = asyncio.run(Renderer().render(greeting_card(props)))
    assert 'class="greeting-card"' in body
    assert "Ada Lovelace" in body
    assert "First programmer." in body
    assert "<button" in body