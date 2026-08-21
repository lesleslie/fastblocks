"""Test fixtures shared across the cross-module resolution tests.

Modules in this package perform import-time registration via the
``FastblocksRegistry`` facade so that other test modules (under
``tests/`` proper) can resolve those registrations and assert
identity. The package itself is pytest-ignored (see ``tests/conftest.py``
``collect_ignore``); the actual pytest tests that consume these
fixtures live under ``tests/core/test_resolver_cross_module.py``.
"""