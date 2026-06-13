"""Property-based tests for FastBlocks exceptions using Hypothesis."""

from typing import Any

import pytest
from hypothesis import assume, given, settings, strategies as st
from hypothesis.strategies import (
    booleans,
    dictionaries,
    integers,
    just,
    lists,
    none,
    one_of,
    sampled_from,
    text,
)

from fastblocks.exceptions import (
    ConfigurationError,
    DependencyError,
    DuplicateCaching,
    ErrorCategory,
    ErrorContext,
    ErrorSeverity,
    FastBlocksException,
    MissingCaching,
    RequestNotCachable,
    ResponseNotCachable,
    StarletteCachesException,
)


# Helper strategies
valid_error_id_strategy = text(
    min_size=1, max_size=50, alphabet="abcdefghijklmnopqrstuvwxyz0123456789_"
).filter(lambda x: x.isidentifier() or x.replace("_", "").isalnum())


valid_message_strategy = text(min_size=1, max_size=200)


valid_config_key_strategy = text(
    min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz._"
)

valid_dependency_key_strategy = text(
    min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz_"
)

error_details_strategy = dictionaries(
    keys=text(min_size=1, max_size=30),
    values=one_of(text(), integers(), booleans(), none()),
    min_size=0,
    max_size=10,
)


@pytest.mark.unit
@pytest.mark.property
class TestFastBlocksExceptionProperties:
    """Property-based tests for FastBlocksException."""

    @given(
        valid_message_strategy,
        sampled_from(ErrorCategory),
        sampled_from(ErrorSeverity),
        error_details_strategy,
    )
    @settings(max_examples=100)
    def test_fastblocks_exception_creation(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        details: dict[str, Any],
    ) -> None:
        """Test FastBlocksException creation with various inputs."""
        exc = FastBlocksException(
            message=message,
            category=category,
            severity=severity,
            details=details,
        )

        assert str(exc) == message
        assert exc.message == message
        assert exc.category == category
        assert exc.severity == severity
        assert exc.details == details

    @given(
        valid_message_strategy,
        sampled_from(ErrorCategory),
        sampled_from(ErrorSeverity),
        error_details_strategy,
        one_of(none(), valid_error_id_strategy),
    )
    @settings(max_examples=50)
    def test_fastblocks_exception_to_error_context(
        self,
        message: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        details: dict[str, Any],
        custom_id: str | None,
    ) -> None:
        """Test FastBlocksException.to_error_context() method."""
        exc = FastBlocksException(
            message=message,
            category=category,
            severity=severity,
            details=details,
        )

        context = exc.to_error_context(error_id=custom_id)

        assert isinstance(context, ErrorContext)
        assert context.message == message
        assert context.category == category
        assert context.severity == severity
        assert context.details == details

        if custom_id is not None:
            assert context.error_id == custom_id
        else:
            # Should use class name
            assert "fastblocksexception" in context.error_id.lower()

    @given(
        valid_message_strategy,
        error_details_strategy,
        one_of(none(), integers(min_value=100, max_value=599)),
    )
    @settings(max_examples=50)
    def test_fastblocks_exception_with_status_code(
        self,
        message: str,
        details: dict[str, Any],
        status_code: int | None,
    ) -> None:
        """Test FastBlocksException with status_code parameter."""
        exc = FastBlocksException(
            message=message,
            details=details,
            status_code=status_code,
        )

        assert exc.message == message
        assert exc.details == details
        assert exc.status_code == status_code

    @given(valid_message_strategy)
    @settings(max_examples=30)
    def test_fastblocks_exception_defaults(self, message: str) -> None:
        """Test FastBlocksException with default values."""
        exc = FastBlocksException(message)

        assert exc.message == message
        assert exc.category == ErrorCategory.APPLICATION
        assert exc.severity == ErrorSeverity.ERROR
        assert exc.details == {}
        assert exc.status_code is None


@pytest.mark.unit
@pytest.mark.property
class TestErrorContextProperties:
    """Property-based tests for ErrorContext."""

    @given(
        valid_error_id_strategy,
        sampled_from(ErrorCategory),
        sampled_from(ErrorSeverity),
        valid_message_strategy,
        error_details_strategy,
        one_of(none(), text(min_size=1, max_size=50)),
        one_of(none(), text(min_size=1, max_size=50)),
    )
    @settings(max_examples=100)
    def test_error_context_creation(
        self,
        error_id: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        details: dict[str, Any],
        request_id: str | None,
        user_id: str | None,
    ) -> None:
        """Test ErrorContext creation with various inputs."""
        context = ErrorContext(
            error_id=error_id,
            category=category,
            severity=severity,
            message=message,
            details=details,
            request_id=request_id,
            user_id=user_id,
        )

        assert context.error_id == error_id
        assert context.category == category
        assert context.severity == severity
        assert context.message == message
        assert context.details == details
        assert context.request_id == request_id
        assert context.user_id == user_id

    @given(valid_error_id_strategy, valid_message_strategy)
    @settings(max_examples=30)
    def test_error_context_defaults(
        self, error_id: str, message: str
    ) -> None:
        """Test ErrorContext with default values."""
        context = ErrorContext(
            error_id=error_id,
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message=message,
        )

        assert context.error_id == error_id
        assert context.message == message
        assert context.details is None
        assert context.request_id is None
        assert context.user_id is None


@pytest.mark.unit
@pytest.mark.property
class TestConfigurationErrorProperties:
    """Property-based tests for ConfigurationError."""

    @given(
        valid_message_strategy,
        one_of(none(), valid_config_key_strategy),
    )
    @settings(max_examples=50)
    def test_configuration_error_creation(
        self,
        message: str,
        config_key: str | None,
    ) -> None:
        """Test ConfigurationError creation."""
        error = ConfigurationError(message, config_key)

        assert str(error) == message
        assert error.category == ErrorCategory.CONFIGURATION
        assert error.severity == ErrorSeverity.CRITICAL

        if config_key is not None:
            assert error.details == {"config_key": config_key}
        else:
            assert error.details == {}


@pytest.mark.unit
@pytest.mark.property
class TestDependencyErrorProperties:
    """Property-based tests for DependencyError."""

    @given(
        valid_message_strategy,
        one_of(none(), valid_dependency_key_strategy),
    )
    @settings(max_examples=50)
    def test_dependency_error_creation(
        self,
        message: str,
        dependency_key: str | None,
    ) -> None:
        """Test DependencyError creation."""
        error = DependencyError(message, dependency_key)

        assert str(error) == message
        assert error.category == ErrorCategory.DEPENDENCY
        assert error.severity == ErrorSeverity.ERROR

        if dependency_key is not None:
            assert error.details == {"dependency_key": dependency_key}
        else:
            assert error.details == {}


@pytest.mark.unit
@pytest.mark.property
class TestCachingExceptionsProperties:
    """Property-based tests for caching-related exceptions."""

    @given(valid_message_strategy)
    @settings(max_examples=30)
    def test_starlette_caches_exception(self, message: str) -> None:
        """Test StarletteCachesException creation."""
        exc = StarletteCachesException(message)

        assert str(exc) == message
        assert exc.category == ErrorCategory.CACHING
        assert exc.severity == ErrorSeverity.ERROR

    @given(valid_message_strategy)
    @settings(max_examples=30)
    def test_duplicate_caching(self, message: str) -> None:
        """Test DuplicateCaching exception."""
        exc = DuplicateCaching(message)

        assert str(exc) == message
        assert isinstance(exc, StarletteCachesException)
        assert exc.category == ErrorCategory.CACHING

    @given(valid_message_strategy)
    @settings(max_examples=30)
    def test_missing_caching(self, message: str) -> None:
        """Test MissingCaching exception."""
        exc = MissingCaching(message)

        assert str(exc) == message
        assert isinstance(exc, StarletteCachesException)
        assert exc.category == ErrorCategory.CACHING

    @given(
        sampled_from(["GET", "POST", "PUT", "DELETE", "PATCH"]),
        text(min_size=1, max_size=100, alphabet="/abcdefghijklmnopqrstuvwxyz"),
    )
    @settings(max_examples=30)
    def test_request_not_cachable(self, method: str, path: str) -> None:
        """Test RequestNotCachable exception."""
        from unittest.mock import Mock

        mock_request = Mock()
        mock_request.method = method
        mock_request.url = Mock()
        mock_request.url.path = path

        exc = RequestNotCachable(mock_request)

        assert exc.request is mock_request
        assert isinstance(exc, StarletteCachesException)
        assert str(exc) == f"Request {method} {path} is not cacheable"

    @given(integers(min_value=100, max_value=599))
    @settings(max_examples=30)
    def test_response_not_cachable(self, status_code: int) -> None:
        """Test ResponseNotCachable exception."""
        from unittest.mock import Mock

        mock_response = Mock()
        mock_response.status_code = status_code

        exc = ResponseNotCachable(mock_response)

        assert exc.response is mock_response
        assert isinstance(exc, StarletteCachesException)
        assert str(exc) == f"Response with status {status_code} is not cacheable"


@pytest.mark.unit
@pytest.mark.property
class TestErrorEnums:
    """Property-based tests for error enums."""

    @given(sampled_from(ErrorCategory))
    @settings(max_examples=20)
    def test_error_category_values(self, category: ErrorCategory) -> None:
        """Test that all ErrorCategory values are strings."""
        assert isinstance(category.value, str)
        assert len(category.value) > 0

    @given(sampled_from(ErrorSeverity))
    @settings(max_examples=20)
    def test_error_severity_values(self, severity: ErrorSeverity) -> None:
        """Test that all ErrorSeverity values are strings."""
        assert isinstance(severity.value, str)
        assert len(severity.value) > 0

    @given(sampled_from(ErrorCategory))
    @settings(max_examples=20)
    def test_error_category_string_representation(self, category: ErrorCategory) -> None:
        """Test ErrorCategory string representation."""
        assert str(category) == category.value

    @given(sampled_from(ErrorSeverity))
    @settings(max_examples=20)
    def test_error_severity_string_representation(self, severity: ErrorSeverity) -> None:
        """Test ErrorSeverity string representation."""
        assert str(severity) == severity.value


@pytest.mark.unit
@pytest.mark.property
class TestExceptionInheritance:
    """Property-based tests for exception inheritance."""

    @given(
        valid_message_strategy,
        sampled_from(ErrorCategory),
        error_details_strategy,
    )
    @settings(max_examples=50)
    def test_all_exceptions_are_exceptions(
        self, message: str, category: ErrorCategory, details: dict[str, Any]
    ) -> None:
        """Test that all FastBlocks exceptions inherit from Exception."""
        exc = FastBlocksException(
            message=message, category=category, details=details
        )

        assert isinstance(exc, Exception)

    @given(
        valid_message_strategy,
        one_of(none(), valid_config_key_strategy),
    )
    @settings(max_examples=30)
    def test_configuration_error_inheritance(
        self, message: str, config_key: str | None
    ) -> None:
        """Test ConfigurationError inheritance chain."""
        exc = ConfigurationError(message, config_key)

        assert isinstance(exc, FastBlocksException)
        assert isinstance(exc, Exception)

    @given(
        valid_message_strategy,
        one_of(none(), valid_dependency_key_strategy),
    )
    @settings(max_examples=30)
    def test_dependency_error_inheritance(
        self, message: str, dependency_key: str | None
    ) -> None:
        """Test DependencyError inheritance chain."""
        exc = DependencyError(message, dependency_key)

        assert isinstance(exc, FastBlocksException)
        assert isinstance(exc, Exception)


@pytest.mark.unit
@pytest.mark.property
class TestExceptionDetailsHandling:
    """Property-based tests for exception details handling."""

    @given(
        valid_message_strategy,
        dictionaries(
            keys=text(min_size=1, max_size=30),
            values=one_of(
                text(),
                integers(min_value=-1000, max_value=1000),
                booleans(),
                lists(integers()),
                none(),
            ),
            min_size=0,
            max_size=20,
        ),
    )
    @settings(max_examples=50)
    def test_exception_with_various_detail_types(
        self, message: str, details: dict[str, Any]
    ) -> None:
        """Test FastBlocksException with various detail types."""
        exc = FastBlocksException(message, details=details)

        assert exc.details == details

    @given(valid_message_strategy)
    @settings(max_examples=30)
    def test_exception_with_none_details_converts_to_empty_dict(
        self, message: str
    ) -> None:
        """Test that None details is converted to empty dict."""
        exc = FastBlocksException(message, details=None)

        assert exc.details == {}
        assert isinstance(exc.details, dict)


@pytest.mark.unit
@pytest.mark.property
class TestErrorContextDetailsHandling:
    """Property-based tests for ErrorContext details handling."""

    @given(
        valid_error_id_strategy,
        sampled_from(ErrorCategory),
        sampled_from(ErrorSeverity),
        valid_message_strategy,
        one_of(none(), dictionaries(keys=text(), values=text(), min_size=0, max_size=5)),
    )
    @settings(max_examples=50)
    def test_error_context_with_optional_details(
        self,
        error_id: str,
        category: ErrorCategory,
        severity: ErrorSeverity,
        message: str,
        details: dict[str, Any] | None,
    ) -> None:
        """Test ErrorContext with optional details."""
        context = ErrorContext(
            error_id=error_id,
            category=category,
            severity=severity,
            message=message,
            details=details,
        )

        assert context.details == details

    @given(
        valid_error_id_strategy,
        valid_message_strategy,
        dictionaries(
            keys=text(min_size=1, max_size=20),
            values=text(min_size=0, max_size=100),
            min_size=0,
            max_size=10,
        ),
    )
    @settings(max_examples=30)
    def test_error_context_details_preservation(
        self, error_id: str, message: str, details: dict[str, str]
    ) -> None:
        """Test that ErrorContext preserves details correctly."""
        context = ErrorContext(
            error_id=error_id,
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message=message,
            details=details,
        )

        assert context.details == details
        assert len(context.details) == len(details)


@pytest.mark.unit
@pytest.mark.property
class TestExceptionMessages:
    """Property-based tests for exception messages."""

    @given(
        text(min_size=0, max_size=1000, alphabet="\\x00\\x01\\x02\\x03\\x04\\x05\\x06\\x07\\x08\\x0b\\x0c\\x0e\\x0f\\x10\\x11\\x12\\x13\\x14\\x15\\x16\\x17\\x18\\x19\\x1a\\x1b\\x1c\\x1d\\x1e\\x1f\\x7f"),
    )
    @settings(max_examples=30)
    def test_exception_with_special_characters(self, message: str) -> None:
        """Test FastBlocksException with special characters in message."""
        exc = FastBlocksException(message)

        assert str(exc) == message
        assert exc.message == message

    @given(
        text(min_size=1, max_size=200).filter(lambda x: len(x.strip()) > 0),
    )
    @settings(max_examples=30)
    def test_exception_with_whitespace(self, message: str) -> None:
        """Test FastBlocksException preserves whitespace in message."""
        exc = FastBlocksException(message)

        assert str(exc) == message

    @given(
        lists(
            sampled_from("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789 "),
            min_size=0,
            max_size=50,
        ).map(lambda x: "".join(x))
    )
    @settings(max_examples=30)
    def test_exception_with_various_lengths(self, message: str) -> None:
        """Test FastBlocksException with messages of various lengths."""
        exc = FastBlocksException(message)

        assert len(exc.message) == len(message)


@pytest.mark.unit
@pytest.mark.property
class TestErrorContextEdgeCases:
    """Property-based tests for ErrorContext edge cases."""

    @given(
        text(min_size=1, max_size=100, alphabet="abcdefghijklmnopqrstuvwxyz"),
        text(min_size=0, max_size=1000),
    )
    @settings(max_examples=30)
    def test_error_context_with_long_messages(self, error_id: str, message: str) -> None:
        """Test ErrorContext with very long messages."""
        context = ErrorContext(
            error_id=error_id,
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message=message,
        )

        assert len(context.message) == len(message)

    @given(
        text(min_size=1, max_size=50),
        text(min_size=1, max_size=50),
    )
    @settings(max_examples=30)
    def test_error_context_ids(self, error_id: str, request_id: str) -> None:
        """Test ErrorContext with various ID formats."""
        context = ErrorContext(
            error_id=error_id,
            category=ErrorCategory.APPLICATION,
            severity=ErrorSeverity.ERROR,
            message="test",
            request_id=request_id,
            user_id=None,
        )

        assert context.error_id == error_id
        assert context.request_id == request_id
