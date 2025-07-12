"""FastBlocks Gather Action - Unified component gathering and orchestration.

This action consolidates and streamlines the various gathering patterns found throughout
FastBlocks, providing a unified interface for collecting routes, templates, middleware,
and application components.

The gather action replaces scattered import_module + loop patterns with:
- Parallel processing capabilities
- Standardized error handling and retry logic
- Unified caching strategies
- Consistent debugging and logging
- Better performance through async orchestration

Key modules:
- routes: Route discovery and collection from adapters
- templates: Template component gathering (loaders, extensions, processors, filters)
- middleware: Middleware stack building and position management
- application: Application component initialization and dependency gathering
- models: SQLModel and Pydantic model discovery and collection
- strategies: Common error handling, caching, and parallelization utilities
"""

from typing import Any

from .application import gather_application
from .middleware import gather_middleware
from .models import gather_models
from .routes import gather_routes
from .templates import gather_templates

__all__ = ["gather"]


class Gather:
    @staticmethod
    async def routes(*args: Any, **kwargs: Any) -> Any:
        return await gather_routes(*args, **kwargs)

    @staticmethod
    async def templates(*args: Any, **kwargs: Any) -> Any:
        return await gather_templates(*args, **kwargs)

    @staticmethod
    async def middleware(*args: Any, **kwargs: Any) -> Any:
        return await gather_middleware(*args, **kwargs)

    @staticmethod
    async def application(*args: Any, **kwargs: Any) -> Any:
        return await gather_application(*args, **kwargs)

    @staticmethod
    async def models(*args: Any, **kwargs: Any) -> Any:
        return await gather_models(*args, **kwargs)


gather = Gather()
