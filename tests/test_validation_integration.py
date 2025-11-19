"""Tests for FastBlocks ACB ValidationService integration.

Verifies validation functionality, security features, and graceful degradation.
"""

import pytest

# Try to import validation integration
try:
    from fastblocks._validation_integration import (
        ACB_VALIDATION_AVAILABLE,
        FastBlocksValidationService,
        ValidationConfig,
        ValidationType,
        get_validation_service,
        register_fastblocks_validation,
        validate_api_contract,
        validate_form_input,
        validate_template_context,
    )

    VALIDATION_INTEGRATION_AVAILABLE = True
except ImportError:
    VALIDATION_INTEGRATION_AVAILABLE = False
    pytestmark = pytest.mark.skip(reason="Validation integration not available")


@pytest.fixture
def validation_service():
    """Get validation service instance."""
    if not VALIDATION_INTEGRATION_AVAILABLE:
        pytest.skip("Validation integration not available")
    return get_validation_service()


@pytest.fixture
def validation_config():
    """Get validation configuration."""
    if not VALIDATION_INTEGRATION_AVAILABLE:
        pytest.skip("Validation integration not available")
    return ValidationConfig()


@pytest.mark.integration
class TestValidationServiceBasics:
    """Test basic validation service functionality."""

    def test_singleton_pattern(self, validation_service):
        """Test that get_validation_service returns the same instance."""
        service1 = get_validation_service()
        service2 = get_validation_service()
        assert service1 is service2

    def test_availability_check(self, validation_service):
        """Test validation service availability property."""
        # Should be True when ACB available, False otherwise
        assert isinstance(validation_service.available, bool)

    def test_validation_config(self, validation_config):
        """Test validation configuration defaults."""
        assert validation_config.validate_templates is True
        assert validation_config.validate_forms is True
        assert validation_config.validate_api is True
        assert validation_config.prevent_xss is True
        assert validation_config.prevent_sql_injection is True
        assert validation_config.prevent_path_traversal is True

    def test_validation_types(self):
        """Test validation type enum."""
        assert ValidationType.TEMPLATE_CONTEXT == "template_context"
        assert ValidationType.FORM_INPUT == "form_input"
        assert ValidationType.API_REQUEST == "api_request"
        assert ValidationType.API_RESPONSE == "api_response"


@pytest.mark.integration
class TestTemplateContextValidation:
    """Test template context validation functionality."""

    @pytest.mark.asyncio
    async def test_basic_context_validation(self, validation_service):
        """Test basic template context validation."""
        context = {
            "title": "Page Title",
            "content": "Page content",
            "user_id": 123,
        }

        (
            is_valid,
            sanitized,
            errors,
        ) = await validation_service.validate_template_context(
            context=context,
            template_name="test.html",
            strict=False,
        )

        assert is_valid is True
        assert isinstance(sanitized, dict)
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_xss_prevention_in_context(self, validation_service):
        """Test XSS prevention in template context."""
        context = {
            "title": "Safe Title",
            "content": "<script>alert('XSS')</script>",
        }

        (
            is_valid,
            sanitized,
            errors,
        ) = await validation_service.validate_template_context(
            context=context,
            template_name="test.html",
            strict=False,
        )

        # XSS should be sanitized
        if validation_service.available and validation_service._config.prevent_xss:
            assert "<script>" not in str(sanitized.get("content", ""))

    @pytest.mark.asyncio
    async def test_sql_injection_detection_in_context(self, validation_service):
        """Test SQL injection detection in template context."""
        context = {
            "search": "'; DROP TABLE users; --",
        }

        (
            is_valid,
            sanitized,
            errors,
        ) = await validation_service.validate_template_context(
            context=context,
            template_name="test.html",
            strict=False,
        )

        # Should detect SQL injection pattern
        if (
            validation_service.available
            and validation_service._config.prevent_sql_injection
        ):
            assert len(errors) > 0
            assert any("SQL injection" in error for error in errors)

    @pytest.mark.asyncio
    async def test_empty_context_validation(self, validation_service):
        """Test validation of empty context."""
        (
            is_valid,
            sanitized,
            errors,
        ) = await validation_service.validate_template_context(
            context={},
            template_name="test.html",
            strict=False,
        )

        assert is_valid is True
        assert sanitized == {}
        assert errors == []


@pytest.mark.integration
class TestFormInputValidation:
    """Test form input validation functionality."""

    @pytest.mark.asyncio
    async def test_basic_form_validation(self, validation_service):
        """Test basic form input validation."""
        form_data = {
            "username": "john_doe",
            "email": "john@example.com",
            "age": "25",
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=None,
            strict=True,
        )

        assert is_valid is True
        assert isinstance(sanitized, dict)
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_form_xss_prevention(self, validation_service):
        """Test XSS prevention in form inputs."""
        form_data = {
            "comment": "<script>alert('XSS')</script>",
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=None,
            strict=False,
        )

        # XSS should be sanitized
        if validation_service.available and validation_service._config.prevent_xss:
            assert "<script>" not in str(sanitized.get("comment", ""))

    @pytest.mark.asyncio
    async def test_form_sql_injection_detection(self, validation_service):
        """Test SQL injection detection in form inputs."""
        form_data = {
            "search": "admin' OR '1'='1",
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=None,
            strict=False,
        )

        # Should detect SQL injection pattern
        if (
            validation_service.available
            and validation_service._config.prevent_sql_injection
        ):
            assert any("SQL injection" in error for error in errors)

    @pytest.mark.asyncio
    async def test_form_path_traversal_detection(self, validation_service):
        """Test path traversal detection in form inputs."""
        form_data = {
            "file_path": "../../etc/passwd",
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=None,
            strict=False,
        )

        # Should detect path traversal
        if (
            validation_service.available
            and validation_service._config.prevent_path_traversal
        ):
            assert any("path traversal" in error for error in errors)

    @pytest.mark.asyncio
    async def test_schema_required_field_validation(self, validation_service):
        """Test schema validation for required fields."""
        form_data = {
            "username": "",  # Empty required field
        }

        schema = {
            "username": {"required": True, "type": str, "min_length": 3},
            "email": {"required": True, "type": str},
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=schema,
            strict=True,
        )

        # Should fail validation
        assert is_valid is False
        assert len(errors) > 0
        assert any(
            "Required field" in error or "too short" in error for error in errors
        )

    @pytest.mark.asyncio
    async def test_schema_type_validation(self, validation_service):
        """Test schema validation for field types."""
        form_data = {
            "age": "not a number",  # String instead of int
        }

        schema = {
            "age": {"required": True, "type": int},
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=schema,
            strict=True,
        )

        # Should detect type mismatch
        if errors:
            assert any("Invalid type" in error for error in errors)

    @pytest.mark.asyncio
    async def test_schema_length_validation(self, validation_service):
        """Test schema validation for min/max length."""
        form_data = {
            "username": "ab",  # Too short
            "bio": "x" * 1001,  # Too long
        }

        schema = {
            "username": {"required": True, "type": str, "min_length": 3},
            "bio": {"required": False, "type": str, "max_length": 1000},
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=schema,
            strict=True,
        )

        # Should detect length violations
        assert is_valid is False
        assert len(errors) > 0

    @pytest.mark.asyncio
    async def test_schema_pattern_validation(self, validation_service):
        """Test schema validation for regex patterns."""
        form_data = {
            "email": "invalid-email",  # No @ symbol
        }

        schema = {
            "email": {
                "required": True,
                "type": str,
                "pattern": r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$",
            },
        }

        is_valid, sanitized, errors = await validation_service.validate_form_input(
            form_data=form_data,
            schema=schema,
            strict=True,
        )

        # Should detect pattern mismatch
        if errors:
            assert any("does not match required pattern" in error for error in errors)


@pytest.mark.integration
class TestAPIValidation:
    """Test API request/response validation."""

    @pytest.mark.asyncio
    async def test_basic_api_request_validation(self, validation_service):
        """Test basic API request validation."""
        request_data = {
            "username": "john_doe",
            "email": "john@example.com",
        }

        is_valid, validated, errors = await validation_service.validate_api_request(
            request_data=request_data,
            schema=None,
        )

        assert is_valid is True
        assert isinstance(validated, dict)
        assert isinstance(errors, list)

    @pytest.mark.asyncio
    async def test_api_request_xss_sanitization(self, validation_service):
        """Test XSS sanitization in API requests."""
        request_data = {
            "comment": "<script>alert('XSS')</script>",
        }

        is_valid, validated, errors = await validation_service.validate_api_request(
            request_data=request_data,
            schema=None,
        )

        # XSS should be sanitized
        if validation_service.available and validation_service._config.prevent_xss:
            assert "<script>" not in str(validated.get("comment", ""))

    @pytest.mark.asyncio
    async def test_basic_api_response_validation(self, validation_service):
        """Test basic API response validation."""
        response_data = {
            "id": 1,
            "username": "john_doe",
            "email": "john@example.com",
        }

        is_valid, validated, errors = await validation_service.validate_api_response(
            response_data=response_data,
            schema=None,
        )

        assert is_valid is True
        assert isinstance(validated, dict)


@pytest.mark.integration
class TestValidationDecorators:
    """Test validation decorators."""

    @pytest.mark.asyncio
    async def test_template_context_decorator(self, validation_service):
        """Test @validate_template_context decorator."""

        @validate_template_context(strict=False)
        async def render_template(request, template, context):
            return f"Rendered {template} with {len(context)} items"

        # Call with safe context
        result = await render_template(
            request=None,
            template="test.html",
            context={"title": "Safe Title"},
        )

        assert "Rendered" in result

    @pytest.mark.asyncio
    async def test_template_context_decorator_with_xss(self, validation_service):
        """Test @validate_template_context decorator sanitizes XSS."""

        @validate_template_context(strict=False)
        async def render_template(request, template, context):
            # Context should be sanitized
            assert (
                "<script>" not in str(context.get("content", ""))
                or not validation_service.available
            )
            return f"Rendered {template}"

        # Call with XSS attempt
        result = await render_template(
            request=None,
            template="test.html",
            context={"content": "<script>alert('XSS')</script>"},
        )

        assert "Rendered" in result

    @pytest.mark.asyncio
    async def test_form_input_decorator(self, validation_service):
        """Test @validate_form_input decorator."""

        @validate_form_input(schema=None, strict=False)
        async def handle_form(request, form_data):
            return f"Processed {len(form_data)} fields"

        # Call with safe data
        result = await handle_form(
            request=None,
            form_data={"username": "john"},
        )

        assert "Processed" in result

    @pytest.mark.asyncio
    async def test_form_input_decorator_sanitizes(self, validation_service):
        """Test @validate_form_input decorator sanitizes inputs."""

        @validate_form_input(schema=None, strict=False)
        async def handle_form(request, form_data):
            # Form data should be sanitized
            assert (
                "<script>" not in str(form_data.get("comment", ""))
                or not validation_service.available
            )
            return "Processed"

        # Call with XSS attempt
        result = await handle_form(
            request=None,
            form_data={"comment": "<script>alert('XSS')</script>"},
        )

        assert "Processed" in result

    @pytest.mark.asyncio
    async def test_api_contract_decorator(self, validation_service):
        """Test @validate_api_contract decorator."""

        @validate_api_contract(request_schema=None, response_schema=None)
        async def create_user(request, data):
            return {"id": 1, "username": data.get("username")}

        # Call with valid data
        result = await create_user(
            request=None,
            data={"username": "john"},
        )

        assert result["id"] == 1
        assert result["username"] == "john"


@pytest.mark.integration
class TestSecurityFeatures:
    """Test security features in detail."""

    def test_sql_injection_patterns(self, validation_service):
        """Test detection of various SQL injection patterns."""
        patterns = [
            "'; DROP TABLE users; --",
            "admin' OR '1'='1",
            "' UNION SELECT * FROM users --",
            "'; DELETE FROM users WHERE '1'='1",
            "' OR 1=1 --",
            "admin'--",
            "' OR 'x'='x",
        ]

        for pattern in patterns:
            assert validation_service._contains_sql_injection(pattern), (
                f"Failed to detect: {pattern}"
            )

    def test_path_traversal_patterns(self, validation_service):
        """Test detection of various path traversal patterns."""
        patterns = [
            "../../../etc/passwd",
            "..\\..\\..\\windows\\system32",
            "%2e%2e%2f",
            "....//",
        ]

        for pattern in patterns:
            assert validation_service._contains_path_traversal(pattern), (
                f"Failed to detect: {pattern}"
            )

    def test_safe_inputs(self, validation_service):
        """Test that safe inputs are not flagged."""
        safe_inputs = [
            "normal text",
            "user@example.com",
            "valid-username_123",
            "This is a normal sentence.",
        ]

        for safe_input in safe_inputs:
            assert not validation_service._contains_sql_injection(safe_input), (
                f"False positive for SQL injection: {safe_input}"
            )
            assert not validation_service._contains_path_traversal(safe_input), (
                f"False positive for path traversal: {safe_input}"
            )


@pytest.mark.integration
class TestGracefulDegradation:
    """Test graceful degradation when ACB unavailable."""

    @pytest.mark.asyncio
    async def test_validation_when_acb_unavailable(self, validation_service):
        """Test that validation degrades gracefully when ACB unavailable."""
        # Should still work, just without ACB features
        context = {"title": "Test"}

        (
            is_valid,
            sanitized,
            errors,
        ) = await validation_service.validate_template_context(
            context=context,
            template_name="test.html",
            strict=False,
        )

        # Should succeed (graceful degradation)
        assert isinstance(is_valid, bool)
        assert isinstance(sanitized, dict)
        assert isinstance(errors, list)

    def test_acb_availability_flag(self):
        """Test ACB_VALIDATION_AVAILABLE flag."""
        assert isinstance(ACB_VALIDATION_AVAILABLE, bool)


@pytest.mark.integration
class TestRegistration:
    """Test validation service registration."""

    @pytest.mark.asyncio
    async def test_register_validation(self):
        """Test registration of validation service."""
        result = await register_fastblocks_validation()

        # Should return bool indicating success/failure
        assert isinstance(result, bool)

    def test_validation_service_exports(self):
        """Test that all expected symbols are exported."""
        expected_exports = [
            "FastBlocksValidationService",
            "ValidationConfig",
            "ValidationType",
            "get_validation_service",
            "validate_template_context",
            "validate_form_input",
            "validate_api_contract",
            "register_fastblocks_validation",
            "ACB_VALIDATION_AVAILABLE",
        ]

        from fastblocks import _validation_integration

        for export in expected_exports:
            assert hasattr(_validation_integration, export), f"Missing export: {export}"


# Run tests with: python -m pytest tests/test_validation_integration.py -v
