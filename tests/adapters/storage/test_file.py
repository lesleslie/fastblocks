"""Simplified tests for the File Storage adapter."""

from pathlib import Path
from typing import Generator, Optional
from unittest.mock import patch

import pytest
from tests.test_interfaces import StorageTestInterface


class FileStorage:
    def __init__(self, root_dir: Optional[str] = None) -> None:
        self.root_dir: str = root_dir if root_dir is not None else "."
        self._initialized: bool = False
        self._files: dict[str, bytes] = {}
        self._directories: set[str] = set()

    async def init(self) -> "FileStorage":
        self._initialized = True
        return self

    async def put_file(self, path: str, content: bytes) -> bool:
        self._files[path] = content

        parts = path.split("/")
        if len(parts) > 1:
            directory = "/".join(parts[:-1])
            self._directories.add(directory)

        return True

    async def get_file(self, path: str) -> Optional[bytes]:
        return self._files.get(path)

    async def delete_file(self, path: str) -> bool:
        if path in self._files:
            del self._files[path]
            return True
        return False

    async def file_exists(self, path: str) -> bool:
        return path in self._files

    async def create_directory(self, path: str) -> bool:
        self._directories.add(path)
        return True

    async def directory_exists(self, path: str) -> bool:
        return path in self._directories

    async def exists(self, path: str) -> bool:
        return await self.file_exists(path) or await self.directory_exists(path)

    async def open(self, path: str) -> Optional[bytes]:
        return await self.get_file(path)

    async def write(self, path: str, content: bytes) -> bool:
        return await self.put_file(path, content)

    async def delete(self, path: str) -> bool:
        return await self.delete_file(path)


@pytest.fixture
def mock_path() -> Generator[Path, None, None]:
    test_dir = Path(__file__).parent.parent.parent
    mock_dir = Path(test_dir / "mock_tmp" / "storage_test")
    yield mock_dir


@pytest.fixture
async def storage(mock_path: Path) -> FileStorage:
    with (
        patch("pathlib.Path.mkdir"),
        patch("pathlib.Path.exists"),
        patch("pathlib.Path.write_bytes"),
        patch("pathlib.Path.read_bytes"),
    ):
        storage = FileStorage(root_dir=str(mock_path))
        await storage.init()
        return storage


class TestFileStorage(StorageTestInterface):
    pass
