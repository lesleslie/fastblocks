"""Tests for Universal Query Parser."""

from unittest.mock import MagicMock

import pytest
from starlette.datastructures import QueryParams
from fastblocks.actions.query.parser import UniversalQueryParser


@pytest.fixture
def mock_request():
    """Create a mock request with query parameters."""
    request = MagicMock()
    request.query_params = QueryParams({})
    return request


@pytest.fixture
def mock_query():
    """Create a mock query interface."""
    query = MagicMock()
    query.for_model = MagicMock(return_value=MagicMock())
    return query


@pytest.fixture
def mock_model_class():
    """Create a mock model class."""
    model = MagicMock()
    model.__name__ = "TestModel"
    return model


class TestUniversalQueryParser:
    """Test UniversalQueryParser functionality."""

    def test_parser_initialization(self, mock_request, mock_query, mock_model_class):
        """Test parser initializes with correct defaults."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser.request == mock_request
        assert parser.model_class == mock_model_class
        assert parser.pattern == "advanced"
        assert parser.default_limit == 10
        assert parser.max_limit == 100
        assert parser.query == mock_query

    def test_parse_pagination_default(self, mock_request, mock_query, mock_model_class):
        """Test pagination with default values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        page, limit, offset = parser._parse_pagination({})

        assert page == 1
        assert limit == 10
        assert offset == 0

    def test_parse_pagination_custom(self, mock_request, mock_query, mock_model_class):
        """Test pagination with custom values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        page, limit, offset = parser._parse_pagination({"page": "3", "limit": "25"})

        assert page == 3
        assert limit == 25
        assert offset == 50  # (page - 1) * limit

    def test_parse_pagination_max_limit(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test pagination respects max limit."""
        parser = UniversalQueryParser(
            mock_request, mock_query, mock_model_class, max_limit=50
        )

        _, limit, _ = parser._parse_pagination({"limit": "200"})

        assert limit == 50

    def test_parse_pagination_invalid_values(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test pagination handles invalid values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        page, limit, offset = parser._parse_pagination({"page": "0", "limit": "-5"})

        assert page == 1  # Minimum is 1
        assert limit == 1  # Minimum is 1
        assert offset == 0

    def test_parse_sorting_default(self, mock_request, mock_query, mock_model_class):
        """Test sorting with default values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        order_by, order_dir = parser._parse_sorting({})

        assert order_by is None
        assert order_dir == "asc"

    def test_parse_sorting_custom(self, mock_request, mock_query, mock_model_class):
        """Test sorting with custom values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        order_by, order_dir = parser._parse_sorting(
            {"order_by": "created_at", "order_dir": "desc"}
        )

        assert order_by == "created_at"
        assert order_dir == "desc"

    def test_parse_sorting_invalid_direction(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test sorting with invalid direction falls back to asc."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        _, order_dir = parser._parse_sorting(
            {"order_by": "name", "order_dir": "invalid"}
        )

        assert order_dir == "asc"

    def test_parse_filters_simple(self, mock_request, mock_query, mock_model_class):
        """Test parsing simple filters."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        filters = parser._parse_filters({"name": "John", "status": "active"})

        assert len(filters) == 2
        assert ("name", "equals", "John") in filters
        assert ("status", "equals", "active") in filters

    def test_parse_filters_with_operators(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test parsing filters with operators."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        filters = parser._parse_filters(
            {
                "age__gt": "18",
                "name__contains": "John",
                "tags__in": "python,javascript",
            }
        )

        assert len(filters) == 3
        assert ("age", "gt", 18) in filters
        assert ("name", "contains", "John") in filters
        assert ("tags", "in", ["python", "javascript"]) in filters

    def test_process_operator_value_null(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test processing null operator."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._process_operator_value("null", "true") is True
        assert parser._process_operator_value("null", "false") is False
        assert parser._process_operator_value("null", "1") is True

    def test_process_operator_value_in(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test processing in operator."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        result = parser._process_operator_value("in", "a,b,c")

        assert result == ["a", "b", "c"]

    def test_process_operator_value_comparison(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test processing comparison operators."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._process_operator_value("gt", "10") == 10
        assert parser._process_operator_value("gte", "5.5") == 5.5
        assert parser._process_operator_value("lt", "100") == 100

    def test_process_simple_value_boolean(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test processing boolean values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._process_simple_value("true") is True
        assert parser._process_simple_value("false") is False
        assert parser._process_simple_value("True") is True
        assert parser._process_simple_value("FALSE") is False

    def test_process_simple_value_null(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test processing null values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._process_simple_value("null") is None
        assert parser._process_simple_value("none") is None
        assert parser._process_simple_value("NULL") is None

    def test_process_simple_value_number(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test processing numeric values."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._process_simple_value("42") == 42
        assert parser._process_simple_value("3.14") == 3.14

    def test_convert_to_number_integer(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test converting to integer."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._convert_to_number("42") == 42
        assert isinstance(parser._convert_to_number("42"), int)

    def test_convert_to_number_float(self, mock_request, mock_query, mock_model_class):
        """Test converting to float."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._convert_to_number("3.14") == 3.14
        assert isinstance(parser._convert_to_number("3.14"), float)

    def test_convert_to_number_invalid(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test converting invalid number returns original."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._convert_to_number("not_a_number") == "not_a_number"

    def test_get_pagination_info_default(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test getting pagination info with defaults."""
        mock_request.query_params = QueryParams({})
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        info = parser.get_pagination_info()

        assert info["page"] == 1
        assert info["limit"] == 10
        assert info["offset"] == 0
        assert info["has_prev"] is False
        assert info["prev_page"] is None
        assert info["next_page"] == 2

    def test_get_pagination_info_custom(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test getting pagination info with custom values."""
        mock_request.query_params = QueryParams({"page": "3", "limit": "20"})
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        info = parser.get_pagination_info()

        assert info["page"] == 3
        assert info["limit"] == 20
        assert info["offset"] == 40
        assert info["has_prev"] is True
        assert info["prev_page"] == 2
        assert info["next_page"] == 4

    def test_validate_query_requirements_no_model(self, mock_request, mock_query):
        """Test validation fails without model class."""
        parser = UniversalQueryParser(mock_request, mock_query, None)

        assert parser._validate_query_requirements() is False

    def test_validate_query_requirements_no_query(self, mock_request, mock_model_class):
        """Test validation fails without query interface."""
        parser = UniversalQueryParser(mock_request, None, mock_model_class)

        assert parser._validate_query_requirements() is False

    def test_validate_query_requirements_success(
        self, mock_request, mock_query, mock_model_class
    ):
        """Test validation succeeds with both model and query."""
        parser = UniversalQueryParser(mock_request, mock_query, mock_model_class)

        assert parser._validate_query_requirements() is True

    @pytest.mark.asyncio
    async def test_parse_and_execute_no_model(self, mock_request, mock_query):
        """Test parse_and_execute returns empty list without model."""
        parser = UniversalQueryParser(mock_request, mock_query, None)

        results = await parser.parse_and_execute()

        assert results == []

    @pytest.mark.asyncio
    async def test_get_count_no_model(self, mock_request, mock_query):
        """Test get_count returns 0 without model."""
        parser = UniversalQueryParser(mock_request, mock_query, None)

        count = await parser.get_count()

        assert count == 0
