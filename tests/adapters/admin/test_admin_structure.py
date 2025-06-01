from pathlib import Path

import pytest


@pytest.mark.unit
class TestAdminStructure:
    def test_admin_base_structure(self) -> None:
        base_file_path = (
            "/Users/les/Projects/fastblocks/fastblocks/adapters/admin/_base.py"
        )

        source_code = Path(base_file_path).read_text()

        assert "class AdminBaseSettings" in source_code
        assert "class AdminBase" in source_code

        assert "style:" in source_code
        assert "title:" in source_code

    def test_sqladmin_structure(self) -> None:
        sqladmin_file_path = (
            "/Users/les/Projects/fastblocks/fastblocks/adapters/admin/sqladmin.py"
        )

        source_code = Path(sqladmin_file_path).read_text()

        assert "class AdminSettings" in source_code
        assert "class Admin" in source_code

        assert "depends.set(Admin)" in source_code
