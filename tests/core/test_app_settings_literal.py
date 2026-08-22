"""Phase 2 mechanical-four Commit2 — AppBaseSettings Literal validation.

Tests that ``AppBaseSettings.style`` is now typed ``StyleName`` and
Pydantic v2 enforces the Literal at construction time. Per the spec
§Data flow Scenario1 caveat, the production ``app.yml`` wiring is
deferred to Phase 2.5; these tests exercise the type via direct
construction.

Legal values: ``vanilla``, ``fastblocks_ui``.
Illegal values: ``kelp``, ``webawesome``, ``bulma`` (all Phase 1A
deleted), plus ``VANILLA`` (case-sensitivity check).
"""
from __future__ import annotations

import pytest
from fastblocks.adapters.app._base import AppBaseSettings


@pytest.mark.unit
def test_legal_style_vanilla_passes() -> None:
    settings = AppBaseSettings(style="vanilla")
    assert settings.style == "vanilla"


@pytest.mark.unit
def test_legal_style_fastblocks_ui_passes() -> None:
    settings = AppBaseSettings(style="fastblocks_ui")
    assert settings.style == "fastblocks_ui"


@pytest.mark.unit
def test_default_style_is_fastblocks_ui() -> None:
    settings = AppBaseSettings()
    assert settings.style == "fastblocks_ui", (
        "DEFAULT_STYLE in core/validators.py is 'fastblocks_ui' but "
        "AppBaseSettings's default field value diverges"
    )


@pytest.mark.unit
@pytest.mark.parametrize(
    "illegal_value",
    ["kelp", "webawesome", "bulma", "VANILLA"],
)
def test_illegal_style_raises_validation_error(illegal_value: str) -> None:
    import pydantic

    with pytest.raises(pydantic.ValidationError) as excinfo:
        AppBaseSettings(style=illegal_value)
    error_msg = str(excinfo.value)
    assert "vanilla" in error_msg, (
        f"Pydantic error must name legal values; got: {error_msg!r}"
    )
    assert "fastblocks_ui" in error_msg, (
        f"Pydantic error must name legal values; got: {error_msg!r}"
    )
    assert illegal_value in error_msg, (
        f"Pydantic error must name the offending value; got: {error_msg!r}"
    )
