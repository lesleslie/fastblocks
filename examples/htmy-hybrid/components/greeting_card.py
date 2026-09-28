"""Greeting card component — HTMY type-safe rendering.

Defines the props dataclass and the HTMY function-component that both
the pure-HTMY mode and the hybrid (HTMY-in-Jinja2) mode render.

# req: REQ-P2-B3-002
"""
from __future__ import annotations

from dataclasses import dataclass

from htmy import Component, Context, component, html


@dataclass(frozen=True, slots=True)
class GreetingCardProps:
    """Immutable input contract for the GreetingCard HTMY component."""

    name: str
    avatar: str
    bio: str


@component
def greeting_card(props: GreetingCardProps, context: Context) -> Component:
    """Render the canonical greeting-card DOM subtree.

    Uses the HTMY ``@component`` decorator pattern — HTMY's ``Component``
    is a Union type, not a base class, so ``class GreetingCard(Component)``
    does not subclass. The decorator wraps it into a callable that takes
    the props and returns the rendered subtree.

    Children are passed positionally to HTMY's ``Tag`` factory (the
    ``children=`` kwarg is rendered as a literal attribute — see
    ``report/fastblocks_ui_macro_deviations``).
    """
    return html.div(
        html.img(src=props.avatar, alt=f"{props.name}'s avatar"),
        html.h2(props.name),
        html.p(props.bio),
        html.button("Follow", type_="button"),
        class_="greeting-card",
    )
