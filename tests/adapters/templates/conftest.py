"""Conftest for templates test configuration."""

import pytest


def pytest_ignore_collect(path, config):
    """Ignore collection of test_components directory."""
    if "test_components" in str(path):
        return True
    return False
