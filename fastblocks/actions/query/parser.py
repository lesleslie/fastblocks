"""Universal Query Parser for FastBlocks.

Converts HTTP request query parameters into ACB universal database queries.
Provides automatic filtering, pagination, sorting, and model lookup capabilities.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-01-13
"""

import typing as t
from contextlib import suppress

from acb.debug import debug
from acb.depends import Inject, depends
from starlette.requests import Request
from fastblocks.htmx import HtmxRequest


class UniversalQueryParser:
    @depends.inject
    def __init__(
        self,
        request: HtmxRequest | Request,
        query: Inject[t.Any],
        model_class: t.Any = None,
        pattern: str = "advanced",
        default_limit: int = 10,
        max_limit: int = 100,
    ) -> None:
        self.request = request
        self.model_class = model_class
        self.pattern = pattern
        self.default_limit = default_limit
        self.max_limit = max_limit
        self.query = query

    def _parse_pagination(self, params: dict[str, str]) -> tuple[int, int, int]:
        page = max(1, int(params.pop("page", 1)))
        limit = min(
            self.max_limit, max(1, int(params.pop("limit", self.default_limit)))
        )
        offset = (page - 1) * limit
        debug(f"Pagination: page={page}, limit={limit}, offset={offset}")
        return page, limit, offset

    def _parse_sorting(self, params: dict[str, str]) -> tuple[str | None, str]:
        order_by = params.pop("order_by", None)
        order_dir = params.pop("order_dir", "asc").lower()
        if order_dir not in ("asc", "desc"):
            order_dir = "asc"
        debug(f"Sorting: order_by={order_by}, order_dir={order_dir}")
        return order_by, order_dir

    def _parse_filters(self, params: dict[str, str]) -> list[tuple[str, str, t.Any]]:
        filters = []
        for key, value in params.items():
            if "__" in key:
                field, operator = key.rsplit("__", 1)
                processed_value = self._process_operator_value(operator, value)
                filters.append((field, operator, processed_value))
            else:
                processed_value = self._process_simple_value(value)
                filters.append((key, "equals", processed_value))
        debug(f"Filters: {filters}")
        return filters

    def _process_operator_value(self, operator: str, value: str) -> t.Any:
        if operator == "null":
            return value.lower() in ("true", "1", "yes")
        elif operator == "in":
            return [v.strip() for v in value.split(",")]
        elif operator in ("gt", "gte", "lt", "lte"):
            return self._convert_to_number(value)
        return value

    def _process_simple_value(self, value: str) -> t.Any:
        if value.lower() in ("true", "false"):
            return value.lower() == "true"
        elif value.lower() in ("null", "none"):
            return None
        return self._convert_to_number(value)

    def _convert_to_number(self, value: str) -> t.Any:
        with suppress(ValueError):
            if "." in value:
                return float(value)

            return int(value)
        return value

    def _apply_operator_filter(
        self, query_builder: t.Any, field: str, operator: str, value: t.Any
    ) -> t.Any:
        """Apply a single filter based on operator."""
        if operator == "equals":
            query_builder = query_builder.where(field, value)
        elif operator == "gt":
            query_builder = query_builder.where_gt(field, value)
        elif operator == "gte":
            query_builder = query_builder.where_gte(field, value)
        elif operator == "lt":
            query_builder = query_builder.where_lt(field, value)
        elif operator == "lte":
            query_builder = query_builder.where_lte(field, value)
        elif operator == "contains":
            query_builder = query_builder.where_like(field, f"%{value}%")
        elif operator == "icontains":
            query_builder = query_builder.where_ilike(field, f"%{value}%")
        elif operator == "in":
            query_builder = query_builder.where_in(field, value)
        elif operator == "not":
            query_builder = query_builder.where_not(field, value)
        elif operator == "null":
            if value:
                query_builder = query_builder.where_null(field)
            else:
                query_builder = query_builder.where_not_null(field)
        else:
            debug(f"Unknown operator '{operator}' for field '{field}', skipping")
        return query_builder

    def _apply_filters(  # noqa: C901
        self, query_builder: t.Any, filters: list[tuple[str, str, t.Any]]
    ) -> t.Any:
        for field, operator, value in filters:
            try:
                query_builder = self._apply_operator_filter(
                    query_builder, field, operator, value
                )
            except AttributeError as e:
                debug(
                    f"Query builder method not available for operator '{operator}': {e}"
                )

        return query_builder

    def _apply_sorting(
        self, query_builder: t.Any, order_by: str | None, order_dir: str
    ) -> t.Any:
        if order_by:
            try:
                if order_dir == "desc":
                    query_builder = query_builder.order_by_desc(order_by)
                else:
                    query_builder = query_builder.order_by(order_by)
            except AttributeError as e:
                debug(f"Query builder sorting method not available: {e}")

        return query_builder

    def _apply_pagination(self, query_builder: t.Any, offset: int, limit: int) -> t.Any:
        try:
            return query_builder.offset(offset).limit(limit)
        except AttributeError as e:
            debug(f"Query builder pagination method not available: {e}")
            return query_builder

    async def parse_and_execute(self) -> list[t.Any]:
        if not self._validate_query_requirements():
            return []
        params = dict(getattr(self.request, "query_params", {}))
        debug(f"Original query params: {params}")
        _, limit, offset = self._parse_pagination(params)
        order_by, order_dir = self._parse_sorting(params)
        filters = self._parse_filters(params)
        try:
            query_builder = self._get_query_builder(filters)
            if query_builder is None:
                return []

            return await self._execute_query(
                query_builder, filters, order_by, order_dir, offset, limit
            )
        except Exception as e:
            debug(f"Query execution failed: {e}")
            return []

    def _validate_query_requirements(self) -> bool:
        if not self.model_class:
            debug("No model class provided for query parsing")
            return False
        if not self.query:
            debug("Universal query interface not available")
            return False
        return True

    def _get_query_builder(self, filters: list[tuple[str, str, t.Any]]) -> t.Any:
        if self.pattern == "simple":
            return self._handle_simple_pattern(filters)
        elif self.pattern in ("repository", "specification"):
            debug(
                f"{self.pattern.title()} pattern not fully implemented, falling back to advanced"
            )
            return self.query.for_model(self.model_class).advanced
        return self.query.for_model(self.model_class).advanced

    def _handle_simple_pattern(self, filters: list[tuple[str, str, t.Any]]) -> t.Any:
        query_builder = self.query.for_model(self.model_class).simple
        if filters:
            for field, operator, value in filters:
                if operator == "equals":
                    try:
                        query_builder = query_builder.where(field, value)
                    except AttributeError:
                        debug("Simple query pattern doesn't support where clause")
                        break
        return query_builder

    async def _execute_query(
        self,
        query_builder: t.Any,
        filters: list[tuple[str, str, t.Any]],
        order_by: str | None,
        order_dir: str,
        offset: int,
        limit: int,
    ) -> list[t.Any]:
        if self.pattern == "simple":
            return t.cast(list[t.Any], await query_builder.all())

        query_builder = self._apply_filters(query_builder, filters)
        query_builder = self._apply_sorting(query_builder, order_by, order_dir)
        query_builder = self._apply_pagination(query_builder, offset, limit)

        debug(f"Executing query for model {self.model_class.__name__}")
        results = t.cast(list[t.Any], await query_builder.all())
        debug(f"Query returned {len(results)} results")

        return results

    async def get_count(self) -> int:
        if not self.model_class or not self.query:
            return 0
        params = dict(getattr(self.request, "query_params", {}))
        params.pop("page", None)
        params.pop("limit", None)
        params.pop("order_by", None)
        params.pop("order_dir", None)
        filters = self._parse_filters(params)
        try:
            query_builder = self.query.for_model(self.model_class).advanced
            query_builder = self._apply_filters(query_builder, filters)

            return t.cast(int, await query_builder.count())
        except Exception as e:
            debug(f"Count query failed: {e}")
            return 0

    def get_pagination_info(self) -> dict[str, t.Any]:
        params = dict(getattr(self.request, "query_params", {}))
        page, limit, offset = self._parse_pagination(params)

        return {
            "page": page,
            "limit": limit,
            "offset": offset,
            "has_prev": page > 1,
            "prev_page": page - 1 if page > 1 else None,
            "next_page": page + 1,
        }


async def get_model_for_query(model_name: str) -> t.Any | None:
    try:
        models = await depends.get("models")
        if models and hasattr(models, model_name):
            return getattr(models, model_name)
    except Exception as e:
        debug(f"Failed to get model '{model_name}': {e}")

    return None


async def create_query_context(
    request: HtmxRequest | Request,
    model_name: str | None = None,
    base_context: dict[str, t.Any] | None = None,
) -> dict[str, t.Any]:
    if base_context is None:
        base_context = {}

    context = dict(base_context)

    if not model_name:
        query_params = getattr(request, "query_params", {})
        model_name = query_params.get("model")

    if not model_name:
        return context

    model_class = await get_model_for_query(model_name)
    if not model_class:
        debug(f"Model '{model_name}' not found")
        return context

    parser = UniversalQueryParser(request, model_class)

    context.update(
        {
            f"{model_name}_parser": parser,
            f"{model_name}_pagination": parser.get_pagination_info(),
            "universal_query": {
                "model_name": model_name,
                "model_class": model_class,
                "parser": parser,
            },
        }
    )

    return context
