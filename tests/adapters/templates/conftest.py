"""Conftest for templates test configuration."""

from pathlib import Path


def pytest_ignore_collect(collection_path: Path, config):
    """Ignore collection of test_components directory."""
    if "test_components" in str(collection_path):
        return True
    return False
