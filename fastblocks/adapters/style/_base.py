"""Base classes and protocols for style adapters."""

from __future__ import annotations

from typing import Any, Protocol
from uuid import UUID

# Oneiric imports
from oneiric.core.config import OneiricSettings
from oneiric.core.resolution import Resolver
from pydantic import Field

from ..oneiric_helper import register_candidate

# Oneiric resolver for dependency injection
depends = Resolver()


class StyleBaseSettings(OneiricSettings):  # type: ignore[misc]
    """Base settings for style adapters using OneiricSettings."""

    cdn_url: str | None = None
    version: str = "latest"
    additional_stylesheets: list[str] = Field(default_factory=list)

    def __init__(self, **data: Any) -> None:
        super().__init__(**data)


class StyleProtocol(Protocol):
    """Protocol for style adapter implementations."""

    def get_stylesheet_links(self) -> list[str]: ...
    def get_component_class(self, component: str) -> str: ...


class StyleBase:
    """Base class for style adapters using Oneiric patterns."""

    # Oneiric-compatible metadata
    MODULE_ID: UUID = UUID("01937d86-4f2a-7b3c-8d9e-f3b4d3c2b1a2")  # Static UUID7
    MODULE_STATUS = "stable"

    def __init__(self) -> None:
        """Initialize style adapter."""
        # Register with Oneiric resolver
        register_candidate(
            depends,
            domain="fastblocks",
            key="styles",
            factory=lambda: self,
            metadata={
                "class": self.__class__.__name__,
                "module": self.__class__.__module__,
            },
        )

    def get_stylesheet_links(self) -> list[str]:
        """Generate stylesheet link tags."""
        raise NotImplementedError()

    def get_component_class(self, component: str) -> str:
        """Get style-specific class names for components."""
        raise NotImplementedError()
