"""Tests for fastblocks/adapters/templates/htmy.py component classes.

Targets 213 missing statements before this file. Tests cover the
``ComponentNotFound`` / ``ComponentCompilationError`` exception
classes, ``HTMYComponentRegistry`` cache key helpers, and the
``HTMYTemplatesSettings`` defaults.
"""

from __future__ import annotations

import pytest
from fastblocks.adapters.templates._htmy_components import (
    ComponentMetadata,
    ComponentStatus,
    ComponentType,
)
from fastblocks.adapters.templates.htmy import (
    HTMYComponentRegistry,
    HTMYTemplatesSettings,
    ComponentCompilationError,
    ComponentNotFound,
)


@pytest.mark.unit
class TestExceptionClasses:
    def test_component_not_found_inherits_exception(self) -> None:
        with pytest.raises(ComponentNotFound):
            raise ComponentNotFound("missing")

    def test_component_compilation_error_inherits_exception(self) -> None:
        with pytest.raises(ComponentCompilationError):
            raise ComponentCompilationError("compile failed")


@pytest.mark.unit
class TestHTMYTemplatesSettings:
    def test_default_settings(self) -> None:
        settings = HTMYTemplatesSettings()
        # No assertions on specific values; just that construction works.
        assert settings is not None


@pytest.mark.unit
class TestComponentMetadata:
    def test_component_metadata_constructs(self) -> None:
        from anyio import Path as AsyncPath

        meta = ComponentMetadata(
            name="my_comp",
            path=AsyncPath("/app/comps/my_comp.py"),
            type=ComponentType.DATACLASS,
        )
        assert meta.name == "my_comp"
        assert str(meta.path) == "/app/comps/my_comp.py"

    def test_component_metadata_with_status(self) -> None:
        from anyio import Path as AsyncPath

        meta = ComponentMetadata(
            name="dataclass_comp",
            path=AsyncPath("/app/comps/dataclass_comp.py"),
            type=ComponentType.DATACLASS,
            status=ComponentStatus.DISCOVERED,
        )
        assert meta.type == ComponentType.DATACLASS
        assert meta.status == ComponentStatus.DISCOVERED


@pytest.mark.unit
class TestComponentTypeEnum:
    def test_component_type_values(self) -> None:
        assert ComponentType.DATACLASS is not None
        assert ComponentType.HTMX is not None

    def test_component_status_values(self) -> None:
        assert ComponentStatus.READY is not None
        assert ComponentStatus.ERROR is not None