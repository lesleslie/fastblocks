"""Shared utilities for icon adapters to reduce complexity."""

from typing import Any


def process_size_attribute(
    size: str | None,
    size_presets: dict[str, str],
    prefix: str,
    attributes: dict[str, Any],
) -> tuple[str, dict[str, Any]]:
    """Process size attribute and return class additions."""
    if not size:
        return "", attributes

    if size in size_presets:
        return f" {prefix}-{size}", attributes

    # Custom size via style
    style = attributes.get("style", "")
    attributes["style"] = f"font-size: {size}; {style}"
    return "", attributes


def process_transformations(
    attributes: dict[str, Any], prefix: str
) -> tuple[str, dict[str, Any]]:
    """Process rotation and flip transformations."""
    classes = []

    if "rotate" in attributes:
        rotation = attributes.pop("rotate")
        if rotation in ("90", "180", "270"):
            classes.append(f"{prefix}-rotate-{rotation}")

    if "flip" in attributes:
        flip = attributes.pop("flip")
        if flip in ("horizontal", "vertical"):
            classes.append(f"{prefix}-flip-{flip}")

    return " ".join(f" {c}" for c in classes), attributes


def process_animations(
    attributes: dict[str, Any], animation_types: list[str], prefix: str
) -> tuple[str, dict[str, Any]]:
    """Process animation attributes."""
    classes = [
        f"{prefix}-{animation}"
        for animation in animation_types
        if animation in attributes and attributes.pop(animation)
    ]

    return " ".join(f" {c}" for c in classes), attributes


def process_semantic_colors(
    attributes: dict[str, Any],
    semantic_colors: list[str],
    prefix: str,
) -> tuple[str, dict[str, Any]]:
    """Process semantic color attributes."""
    if "color" not in attributes:
        return "", attributes

    color = attributes.pop("color")

    if color in semantic_colors:
        return f" {prefix}-{color}", attributes

    # Custom color via style
    style = attributes.get("style", "")
    attributes["style"] = f"color: {color}; {style}"
    return "", attributes


def process_state_attributes(
    attributes: dict[str, Any], prefix: str
) -> tuple[str, dict[str, Any]]:
    """Process interactive and state attributes."""
    classes = []

    if "interactive" in attributes and attributes.pop("interactive"):
        classes.append(f"{prefix}-interactive")

    if "disabled" in attributes and attributes.pop("disabled"):
        classes.append(f"{prefix}-disabled")

    if "loading" in attributes and attributes.pop("loading"):
        classes.append(f"{prefix}-loading")

    if "inactive" in attributes and attributes.pop("inactive"):
        classes.append(f"{prefix}-inactive")

    return " ".join(f" {c}" for c in classes), attributes


def add_accessibility_attributes(attributes: dict[str, Any]) -> dict[str, Any]:
    """Add default accessibility attributes if missing."""
    if "aria-label" not in attributes and "title" not in attributes:
        attributes["aria-hidden"] = "true"
    return attributes


def build_attr_string(attributes: dict[str, Any]) -> str:
    """Build HTML attribute string from dict."""
    return " ".join(f'{k}="{v}"' for k, v in attributes.items() if v is not None)
