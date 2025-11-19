"""Test HTMY component for FastBlocks testing."""

from dataclasses import dataclass
from typing import Any

import pytest

# FastBlocks has its own HTMY implementation, doesn't use the htmy library
Component = Any
Context = dict


def component(x):
    return x


HTMY_AVAILABLE = False


@dataclass
@pytest.mark.unit
class TestCard:
    """Simple test card component for FastBlocks HTMY integration."""

    title: str = "Test Component"
    content: str = "Test content"
    theme: str = "default"

    def htmy(self, context: Context) -> Component:
        """Render the test card component."""
        if HTMY_AVAILABLE:

            @component
            def test_card_component(props, ctx) -> str:
                return f"""
                <div class="test-card {self.theme}">
                    <h3>{self.title}</h3>
                    <p>{self.content}</p>
                    <span>FastBlocks HTMY Integration Test Success!</span>
                </div>
                """

            return test_card_component(context)
        else:
            # Fallback HTML generation
            return f"""
            <div class="test-card {self.theme}">
                <h3>{self.title}</h3>
                <p>{self.content}</p>
                <span>FastBlocks HTMY Integration Test Success!</span>
            </div>
            """
