"""Reusable design patterns for fastblocks."""

from __future__ import annotations

import threading


class SingletonMeta(type):
    """Thread-safe singleton metaclass.

    Replaces the `_instance + __new__ + hasattr` guard pattern that
    was duplicated 4× across `_events_integration`, `_health_integration`,
    `_validation_integration`, and `_workflows_integration`.
    """

    _instances: dict[type, object] = {}
    _lock = threading.Lock()

    def __call__(cls, *args: object, **kwargs: object) -> object:
        with cls._lock:
            if cls not in cls._instances:
                cls._instances[cls] = super().__call__(*args, **kwargs)
        return cls._instances[cls]
