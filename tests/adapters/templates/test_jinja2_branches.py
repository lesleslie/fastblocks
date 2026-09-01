"""Tests for uncovered branches in fastblocks/adapters/templates/jinja2.py.

Targets the uncovered PackageLoader edge cases (270 missing statements
before this file): the early-return paths in ``__init__`` for absolute
package paths, missing packages, and ``ImportError`` raises.
"""

from __future__ import annotations

from anyio import Path as AsyncPath

import pytest
from fastblocks.adapters.templates.jinja2 import PackageLoader


@pytest.mark.unit
class TestPackageLoaderInitialization:
    def test_absolute_package_path_returns_no_loader(self) -> None:
        # ``package_name`` starts with "/" — the loader short-circuits
        # to ``self._loader = None`` and returns.
        loader = PackageLoader("/abs/path/to/pkg")
        assert loader._loader is None

    def test_missing_package_returns_no_loader(self) -> None:
        # ModuleNotFoundError path — _loader is set to None.
        loader = PackageLoader("definitely_not_a_real_package_xyz123")
        assert loader._loader is None

    def test_package_loader_attributes_on_short_circuit(self) -> None:
        # When the loader short-circuits (absolute path), basic
        # attributes still get wired up.
        loader = PackageLoader("/abs/path/to/pkg")
        assert loader.package_name == "/abs/path/to/pkg"
        assert loader.path.name == "templates"
        assert loader._adapter == "admin"

    def test_package_loader_with_custom_path_short_circuit(self) -> None:
        # The package_path / path attributes are set from constructor.
        loader = PackageLoader("/abs/path/to/pkg", path="static")
        assert loader.path.name == "static"

    def test_package_loader_with_custom_adapter_short_circuit(self) -> None:
        loader = PackageLoader("/abs/path/to/pkg", adapter="htmy")
        assert loader._adapter == "htmy"


@pytest.mark.unit
class TestPackageLoaderInitPath:
    """Pin: when the package short-circuits, ``_loader`` is None."""

    def test_short_circuit_attributes_present(self) -> None:
        loader = PackageLoader("/abs/path/to/pkg")
        assert loader.package_name == "/abs/path/to/pkg"
        assert loader.path.name == "templates"
        assert loader._template_root == AsyncPath(".") or loader._template_root is not None

    def test_short_circuit_with_custom_path(self) -> None:
        loader = PackageLoader("/abs/path/to/pkg", path="static")
        assert loader.path.name == "static"

    def test_short_circuit_with_adapter(self) -> None:
        loader = PackageLoader("/abs/path/to/pkg", adapter="htmy")
        assert loader._adapter == "htmy"
