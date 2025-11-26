import pytest


@pytest.mark.unit
class TestIconUtils:
    def test_process_size_attribute_none(self):
        from fastblocks.adapters.icons._utils import process_size_attribute

        cls, attrs = process_size_attribute(
            size=None,
            size_presets={"sm": "0.75rem", "lg": "1.5rem"},
            prefix="fa",
            attributes={"class": "fa-icon"},
        )
        assert cls == ""
        assert attrs == {"class": "fa-icon"}

    def test_process_size_attribute_preset(self):
        from fastblocks.adapters.icons._utils import process_size_attribute

        cls, attrs = process_size_attribute(
            size="lg",
            size_presets={"sm": "0.75rem", "lg": "1.5rem"},
            prefix="fa",
            attributes={},
        )
        assert cls.strip() == "fa-lg"
        assert attrs == {}

    def test_process_size_attribute_custom(self):
        from fastblocks.adapters.icons._utils import process_size_attribute

        cls, attrs = process_size_attribute(
            size="18px",
            size_presets={"sm": "0.75rem"},
            prefix="fa",
            attributes={"style": "color: red;"},
        )
        assert cls == ""
        assert "font-size: 18px;" in attrs["style"]
        assert attrs["style"].strip().endswith("color: red;")

    def test_process_transformations_valid(self):
        from fastblocks.adapters.icons._utils import process_transformations

        cls, attrs = process_transformations(
            {"rotate": "90", "flip": "horizontal", "id": "x"}, prefix="fa"
        )
        # Both rotation and flip are converted to classes and removed from attrs
        assert "fa-rotate-90" in cls
        assert "fa-flip-horizontal" in cls
        assert "rotate" not in attrs and "flip" not in attrs
        assert attrs["id"] == "x"

    def test_process_transformations_invalid_rotation(self):
        from fastblocks.adapters.icons._utils import process_transformations

        # Invalid rotate value is popped and ignored
        cls, attrs = process_transformations({"rotate": "45"}, prefix="fa")
        assert cls == ""
        assert "rotate" not in attrs

    def test_process_animations(self):
        from fastblocks.adapters.icons._utils import process_animations

        attrs = {"spin": True, "pulse": False, "other": 1}
        cls, out = process_animations(attrs, ["spin", "pulse"], prefix="fa")
        assert cls.strip() == "fa-spin"
        # animation keys are popped regardless of truthiness
        assert "spin" not in out and "pulse" not in out
        assert out["other"] == 1

    def test_process_semantic_colors(self):
        from fastblocks.adapters.icons._utils import process_semantic_colors

        # Semantic color
        cls1, attrs1 = process_semantic_colors(
            {"color": "primary"}, ["primary", "danger"], prefix="fa"
        )
        assert cls1.strip() == "fa-primary"
        assert "color" not in attrs1

        # Custom color falls back to style
        cls2, attrs2 = process_semantic_colors(
            {"color": "#f00", "style": "margin:0;"}, ["primary"], prefix="fa"
        )
        assert cls2 == ""
        assert "color: #f00;" in attrs2["style"]
        assert attrs2["style"].strip().endswith("margin:0;")

    def test_process_state_attributes(self):
        from fastblocks.adapters.icons._utils import process_state_attributes

        cls, attrs = process_state_attributes(
            {
                "interactive": True,
                "disabled": False,
                "loading": True,
                "inactive": True,
                "data-x": 1,
            },
            prefix="fa",
        )
        # disabled=False should not produce a class and is popped
        assert "fa-interactive" in cls
        assert "fa-loading" in cls
        assert "fa-inactive" in cls
        assert "disabled" not in attrs
        assert attrs["data-x"] == 1

    def test_accessibility_and_attr_string(self):
        from fastblocks.adapters.icons._utils import (
            add_accessibility_attributes,
            build_attr_string,
        )

        attrs = add_accessibility_attributes({"class": "x"})
        # With no aria-label or title, aria-hidden is added
        assert attrs.get("aria-hidden") == "true"

        # Title present: aria-hidden should not be added
        attrs2 = add_accessibility_attributes({"title": "Icon"})
        assert "aria-hidden" not in attrs2

        s = build_attr_string({"class": "x", "data-a": None, "aria-hidden": "true"})
        assert 'class="x"' in s and 'aria-hidden="true"' in s
        assert "data-a=" not in s
