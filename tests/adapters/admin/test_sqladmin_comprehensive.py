"""Comprehensive tests for the sqladmin adapter."""

from unittest.mock import MagicMock, patch

import pytest
from starlette.applications import Starlette

# Skip all tests in this module if sqladmin is not available
sqladmin = pytest.importorskip("sqladmin")
# Import the module conditionally
fastblocks_sqladmin = pytest.importorskip("fastblocks.adapters.admin.sqladmin")
# Now we can import from the module that we know exists
Admin = fastblocks_sqladmin.Admin
AdminSettings = fastblocks_sqladmin.AdminSettings


@pytest.mark.asyncio
async def test_admin_initialization() -> None:
    """Test the initialization of the Admin class."""
    # Mock dependencies
    mock_app = MagicMock(spec=Starlette)
    mock_templates = MagicMock()
    mock_templates.admin = MagicMock()

    # Mock the SqlAdminBase import from sqladmin
    mock_sqladmin_base = MagicMock()

    # Create the Admin instance
    with patch("sqladmin.Admin", mock_sqladmin_base):
        admin = Admin(app=mock_app, templates=mock_templates, engine="mock_engine")

        # Verify SqlAdminBase was initialized correctly
        mock_sqladmin_base.assert_called_once_with(app=mock_app, engine="mock_engine")

        # Verify templates was set correctly
        assert admin.templates == mock_templates.admin


@pytest.mark.asyncio
async def test_admin_getattr() -> None:
    """Test the __getattr__ method of the Admin class."""
    # Mock dependencies
    mock_app = MagicMock(spec=Starlette)
    mock_templates = MagicMock()
    mock_templates.admin = MagicMock()

    # Create a mock for _sqladmin with a test attribute
    mock_sqladmin = MagicMock()
    mock_sqladmin.test_attribute = "test_value"

    # Create the Admin instance
    with patch(
        "sqladmin.Admin",
        return_value=mock_sqladmin,
    ):
        admin = Admin(app=mock_app, templates=mock_templates)

        # Test __getattr__
        assert admin.test_attribute == "test_value"

        # Test a method call through __getattr__
        admin.add_view("test_model")
        mock_sqladmin.add_view.assert_called_once_with("test_model")


@pytest.mark.asyncio
async def test_admin_init_with_admin_models() -> None:
    """Test the init method with admin models."""
    # Mock dependencies
    mock_app = MagicMock(spec=Starlette)
    mock_templates = MagicMock()
    mock_templates.admin = MagicMock()

    # Create a mock for _sqladmin
    mock_sqladmin = MagicMock()

    # Create mock models with get_admin_models
    mock_models = MagicMock()
    mock_admin_models = [MagicMock(), MagicMock()]
    mock_models.get_admin_models.return_value = mock_admin_models

    # Create the Admin instance
    with patch(
        "sqladmin.Admin",
        return_value=mock_sqladmin,
    ):
        admin = Admin(app=mock_app, templates=mock_templates)

        # Mock depends.get to return our mock models
        with patch(
            "fastblocks.adapters.admin.sqladmin.depends.get", return_value=mock_models
        ):
            # Call init
            await admin.init()

        # Verify add_view was called for each model
        assert mock_sqladmin.add_view.call_count == len(mock_admin_models)
        for model in mock_admin_models:
            mock_sqladmin.add_view.assert_any_call(model)


@pytest.mark.asyncio
async def test_admin_init_without_admin_models() -> None:
    """Test the init method without admin models."""
    # Mock dependencies
    mock_app = MagicMock(spec=Starlette)
    mock_templates = MagicMock()
    mock_templates.admin = MagicMock()

    # Create a mock for _sqladmin
    mock_sqladmin = MagicMock()

    # Create mock models without get_admin_models
    mock_models = MagicMock()
    mock_models.get_admin_models = None

    # Create the Admin instance
    with patch(
        "sqladmin.Admin",
        return_value=mock_sqladmin,
    ):
        admin = Admin(app=mock_app, templates=mock_templates)

        # Mock depends.get to return our mock models
        with patch(
            "fastblocks.adapters.admin.sqladmin.depends.get", return_value=mock_models
        ):
            # Call init
            await admin.init()

        # Verify add_view was not called
        mock_sqladmin.add_view.assert_not_called()


@pytest.mark.asyncio
async def test_admin_settings() -> None:
    """Test the AdminSettings class."""
    # Create an instance of AdminSettings
    settings = AdminSettings()

    # Verify it inherits from AdminBaseSettings
    from fastblocks.adapters.admin._base import AdminBaseSettings

    assert isinstance(settings, AdminBaseSettings)
