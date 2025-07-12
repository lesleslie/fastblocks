import typing as t
from unittest.mock import MagicMock

import pytest
from pytest_mock import MockerFixture


@pytest.fixture
def mock_acb(mocker: MockerFixture) -> t.Any:
    mock_acb = mocker.MagicMock()
    mock_actions = mocker.MagicMock()
    mock_cache = mocker.MagicMock()
    mock_storage = mocker.MagicMock()

    mock_acb.actions = mock_actions
    mock_acb.cache = mock_cache
    mock_acb.storage = mock_storage

    mocker.patch.dict(
        "sys.modules",
        {
            "acb": mock_acb,
            "acb.actions": mock_actions,
            "acb.cache": mock_cache,
            "acb.storage": mock_storage,
            "acb.adapters": MagicMock(),
            "acb.depends": MagicMock(),
        },
    )

    return mock_acb


@pytest.mark.unit
class TestAdminBase:
    def test_admin_base_settings(
        self,
        monkeypatch: pytest.MonkeyPatch,
        mock_acb: t.Any,
    ) -> None:
        from fastblocks.adapters.admin._base import AdminBaseSettings

        settings = AdminBaseSettings()

        assert hasattr(settings, "title")
        assert hasattr(settings, "style")
