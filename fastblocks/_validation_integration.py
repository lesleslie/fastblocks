"""ACB ValidationService integration for FastBlocks.

This module provides validation capabilities using ACB's ValidationService,
with graceful degradation when ACB validation is not available.

Author: lesleslie <les@wedgwoodwebworks.com>
Created: 2025-10-01

Key Features:
- Template context validation and sanitization
- Form input validation with XSS prevention
- API contract validation for endpoints
- Graceful degradation when ValidationService unavailable
- Decorators for automatic validation
- Custom validation schemas for FastBlocks patterns

Usage:
    # Template context validation
    @validate_template_context
    async def render_template(request, template, context):
        ...

    # Form input validation and sanitization
    @validate_form_input
    async def handle_form_submit(request, form_data):
        ...

    # API contract validation
    @validate_api_contract(request_schema=UserCreateSchema, response_schema=UserSchema)
    async def create_user(request):
        ...
"""

import functools
import typing as t
from contextlib import suppress
from dataclasses import dataclass
from enum import Enum

from acb.depends import depends

# Try to import ACB validation components
acb_validation_available = False
ValidationService = None
ValidationSchema = None
InputSanitizer = None
OutputValidator = None
ValidationResult = None
ValidationError = None
validate_input_decorator = None
validate_output_decorator = None
sanitize_input_decorator = None

with suppress(ImportError):
    from acb.services.validation import (  # type: ignore[no-redef]
        InputSanitizer,
        OutputValidator,
    )

    acb_validation_available = True


class ValidationType(str, Enum):
    """Types of validation performed by FastBlocks."""

    TEMPLATE_CONTEXT = "template_context"
    FORM_INPUT = "form_input"
    API_REQUEST = "api_request"
    API_RESPONSE = "api_response"
    ROUTE_PARAMS = "route_params"
    QUERY_PARAMS = "query_params"


@dataclass
class ValidationConfig:
    """Configuration for FastBlocks validation integration."""

    # Enable/disable specific validation types
    validate_templates: bool = True
    validate_forms: bool = True
    validate_api: bool = True

    # Security settings
    prevent_xss: bool = True
    prevent_sql_injection: bool = True
    prevent_path_traversal: bool = True

    # Performance settings
    cache_validation_results: bool = True
    validation_timeout_ms: float = 100.0

    # Reporting
    collect_validation_metrics: bool = True
    log_validation_failures: bool = True


class FastBlocksValidationService:
    """FastBlocks wrapper for ACB ValidationService with graceful degradation."""

    _instance: t.ClassVar["FastBlocksValidationService | None"] = None
    _config: t.ClassVar[ValidationConfig] = ValidationConfig()

    def __new__(cls) -> "FastBlocksValidationService":
        """Singleton pattern - ensure only one instance exists."""
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self) -> None:
        """Initialize validation service with ACB integration."""
        if not hasattr(self, "_initialized"):
            self._service: t.Any = None  # ValidationService when ACB available
            self._sanitizer: t.Any = None  # InputSanitizer when ACB available
            self._validator: t.Any = None  # OutputValidator when ACB available
            self._initialized = True

            # Try to get ACB ValidationService
            if acb_validation_available:
                with suppress(Exception):
                    self._service = depends.get("validation_service")
                    if self._service:
                        self._sanitizer = InputSanitizer()  # type: ignore[operator]
                        self._validator = OutputValidator()  # type: ignore[operator]

    @property
    def available(self) -> bool:
        """Check if ACB ValidationService is available."""
        return acb_validation_available and self._service is not None

    def _sanitize_context_value(
        self,
        key: str,
        value: t.Any,
        errors: list[str],
    ) -> t.Any:
        """Sanitize a single context value.

        Args:
            key: Context key
            value: Context value
            errors: Error list to append to

        Returns:
            Sanitized value
        """
        # Skip non-string values (they're safe)
        if not isinstance(value, str):
            return value

        # Sanitize string values for XSS
        if self._config.prevent_xss and self._sanitizer:
            try:
                return self._sanitizer.sanitize_html(value)
            except Exception as e:
                errors.append(f"Failed to sanitize {key}: {e}")
                return value

        return value

    def _check_sql_injection_in_context(
        self,
        sanitized: dict[str, t.Any],
        errors: list[str],
        strict: bool,
    ) -> bool:
        """Check for SQL injection patterns in sanitized context.

        Args:
            sanitized: Sanitized context data
            errors: Error list to append to
            strict: If True, return False immediately on finding issues

        Returns:
            False if strict and issues found, True otherwise
        """
        if not self._config.prevent_sql_injection:
            return True

        for key, value in sanitized.items():
            if isinstance(value, str) and self._contains_sql_injection(value):
                errors.append(f"Potential SQL injection in {key}")
                if strict:
                    return False

        return True

    async def validate_template_context(
        self,
        context: dict[str, t.Any],
        template_name: str,
        strict: bool = False,
    ) -> tuple[bool, dict[str, t.Any], list[str]]:
        """Validate and sanitize template context data.

        Args:
            context: Template context dictionary
            template_name: Name of the template being rendered
            strict: If True, fail on any validation warnings

        Returns:
            Tuple of (is_valid, sanitized_context, error_messages)
        """
        # Guard clause: skip if validation unavailable or disabled
        if not self.available or not self._config.validate_templates:
            return True, context, []

        errors: list[str] = []

        try:
            # Sanitize each context value
            sanitized = {
                key: self._sanitize_context_value(key, value, errors)
                for key, value in context.items()
            }

            # Check for SQL injection patterns
            if not self._check_sql_injection_in_context(sanitized, errors, strict):
                return False, context, errors

            # Validation passed (or warnings only)
            return len(errors) == 0 or not strict, sanitized, errors

        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, context, errors

    async def validate_form_input(
        self,
        form_data: dict[str, t.Any],
        schema: dict[str, t.Any] | None = None,
        strict: bool = True,
    ) -> tuple[bool, dict[str, t.Any], list[str]]:
        """Validate and sanitize form input data.

        Args:
            form_data: Form data to validate
            schema: Optional validation schema (field_name -> rules)
            strict: If True, fail on any validation errors

        Returns:
            Tuple of (is_valid, sanitized_data, error_messages)
        """
        # Guard clause: skip if validation disabled
        if not self._config.validate_forms:
            return True, form_data, []

        errors: list[str] = []

        try:
            # Sanitize and validate fields
            sanitized = self._sanitize_form_fields(form_data, errors)

            # Apply schema validation if provided
            if schema:
                self._apply_schema_validation(sanitized, schema, errors)

            return len(errors) == 0, sanitized, errors

        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, form_data, errors

    def _sanitize_form_fields(
        self,
        form_data: dict[str, t.Any],
        errors: list[str],
    ) -> dict[str, t.Any]:
        """Sanitize all form fields and perform security checks.

        Args:
            form_data: Raw form data
            errors: Error list to append to

        Returns:
            Sanitized form data
        """
        sanitized = {}

        for key, value in form_data.items():
            sanitized[key] = self._sanitize_field(key, value, errors)

            # Security checks for string values
            if isinstance(value, str):
                self._check_security_issues(key, value, errors)

        return sanitized

    def _apply_schema_validation(
        self,
        sanitized_data: dict[str, t.Any],
        schema: dict[str, t.Any],
        errors: list[str],
    ) -> None:
        """Apply schema validation rules to sanitized data.

        Args:
            sanitized_data: Sanitized form data
            schema: Validation schema (field_name -> rules)
            errors: Error list to append to
        """
        for field_name, rules in schema.items():
            value = sanitized_data.get(field_name)
            self._validate_field_schema(field_name, value, rules, errors)

    async def validate_api_request(
        self,
        request_data: dict[str, t.Any],
        schema: t.Any = None,
    ) -> tuple[bool, dict[str, t.Any], list[str]]:
        """Validate API request data against a schema.

        Args:
            request_data: Request data to validate
            schema: Validation schema (Pydantic, msgspec, etc.)

        Returns:
            Tuple of (is_valid, validated_data, error_messages)
        """
        # Guard clause: skip if unavailable or disabled
        if not self.available or not self._config.validate_api:
            return True, request_data, []

        errors: list[str] = []

        try:
            # Try schema validation first
            if schema:
                result = self._validate_with_schema(request_data, schema, errors)
                if result is not None:
                    return result

            # Fallback: basic sanitization
            sanitized = self._sanitize_api_data(request_data)
            return True, sanitized, []

        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, request_data, errors

    def _validate_with_schema(
        self,
        data: dict[str, t.Any],
        schema: t.Any,
        errors: list[str],
    ) -> tuple[bool, dict[str, t.Any], list[str]] | None:
        """Attempt validation with Pydantic or msgspec schema.

        Args:
            data: Data to validate
            schema: Validation schema
            errors: Error list to append to

        Returns:
            Validation result tuple if successful, None to continue with fallback
        """
        # Try Pydantic validation
        if hasattr(schema, "model_validate"):
            try:
                validated = schema.model_validate(data)
                return True, validated.model_dump(), []
            except Exception as e:
                errors.append(f"Pydantic validation failed: {e}")
                return False, data, errors

        # Try msgspec validation
        if hasattr(schema, "__struct_fields__"):
            try:
                import msgspec

                validated = msgspec.convert(data, type=schema)
                return True, msgspec.to_builtins(validated), []
            except Exception as e:
                errors.append(f"msgspec validation failed: {e}")
                return False, data, errors

        return None

    def _sanitize_api_data(self, data: dict[str, t.Any]) -> dict[str, t.Any]:
        """Apply basic XSS sanitization to API data.

        Args:
            data: Data to sanitize

        Returns:
            Sanitized data
        """
        sanitized = {}
        for key, value in data.items():
            if isinstance(value, str) and self._config.prevent_xss and self._sanitizer:
                sanitized[key] = self._sanitizer.sanitize_html(value)
            else:
                sanitized[key] = value
        return sanitized

    async def validate_api_response(
        self,
        response_data: dict[str, t.Any],
        schema: t.Any = None,
    ) -> tuple[bool, dict[str, t.Any], list[str]]:
        """Validate API response data against a schema.

        Args:
            response_data: Response data to validate
            schema: Validation schema (Pydantic, msgspec, etc.)

        Returns:
            Tuple of (is_valid, validated_data, error_messages)
        """
        # Guard clause: skip if unavailable or disabled
        if not self.available or not self._config.validate_api:
            return True, response_data, []

        errors: list[str] = []

        try:
            # Try schema validation if provided
            if schema:
                result = self._validate_response_with_schema(
                    response_data, schema, errors
                )
                if result is not None:
                    return result

            return True, response_data, []

        except Exception as e:
            errors.append(f"Validation error: {e}")
            return False, response_data, errors

    def _validate_response_with_schema(
        self,
        data: dict[str, t.Any],
        schema: t.Any,
        errors: list[str],
    ) -> tuple[bool, dict[str, t.Any], list[str]] | None:
        """Attempt response validation with Pydantic or msgspec schema.

        Args:
            data: Response data to validate
            schema: Validation schema
            errors: Error list to append to

        Returns:
            Validation result tuple if successful, None otherwise
        """
        # Try Pydantic validation
        if hasattr(schema, "model_validate"):
            try:
                validated = schema.model_validate(data)
                return True, validated.model_dump(), []
            except Exception as e:
                errors.append(f"Response validation failed: {e}")
                return False, data, errors

        # Try msgspec validation
        if hasattr(schema, "__struct_fields__"):
            try:
                import msgspec

                validated = msgspec.convert(data, type=schema)
                return True, msgspec.to_builtins(validated), []
            except Exception as e:
                errors.append(f"Response validation failed: {e}")
                return False, data, errors

        return None

    def _contains_sql_injection(self, value: str) -> bool:
        """Check for common SQL injection patterns."""
        sql_patterns = [
            "union select",
            "union all select",
            "drop table",
            "delete from",
            "insert into",
            "update set",
            "'; --",
            "'--",
            "' or '1'='1",
            "' or 1=1",
            '" or "1"="1',
            "or 1=1",
            "' or 'x'='x",
            '" or "x"="x',
            "admin'--",
            'admin"--',
            "') or ('1'='1",
            '") or ("1"="1',
            "exec(",
            "execute(",
            "xp_cmdshell",
            "sp_executesql",
        ]
        value_lower = value.lower()
        return any(pattern in value_lower for pattern in sql_patterns)

    def _contains_path_traversal(self, value: str) -> bool:
        """Check for path traversal attempts."""
        traversal_patterns = ["../", "..\\", "%2e%2e", "....//"]
        return any(pattern in value.lower() for pattern in traversal_patterns)

    def _sanitize_field(
        self,
        key: str,
        value: t.Any,
        errors: list[str],
    ) -> t.Any:
        """Sanitize a single form field.

        Args:
            key: Field name
            value: Field value
            errors: Error list to append to

        Returns:
            Sanitized value
        """
        # Skip non-string values
        if not isinstance(value, str):
            return value

        # Sanitize for XSS (only if ACB available)
        if self.available and self._config.prevent_xss and self._sanitizer:
            try:
                return self._sanitizer.sanitize_html(value)
            except Exception as e:
                errors.append(f"Failed to sanitize {key}: {e}")
                return value

        return value

    def _check_security_issues(
        self,
        key: str,
        value: str,
        errors: list[str],
    ) -> None:
        """Check for security issues in form field.

        Args:
            key: Field name
            value: Field value
            errors: Error list to append to
        """
        if not self.available:
            return

        # Check for SQL injection
        if self._config.prevent_sql_injection:
            if self._contains_sql_injection(value):
                errors.append(f"Potential SQL injection in {key}")

        # Check for path traversal
        if self._config.prevent_path_traversal:
            if self._contains_path_traversal(value):
                errors.append(f"Potential path traversal in {key}")

    def _validate_field_schema(
        self,
        field_name: str,
        value: t.Any,
        rules: dict[str, t.Any],
        errors: list[str],
    ) -> None:
        """Validate a field against its schema rules.

        Args:
            field_name: Field name
            value: Field value
            rules: Validation rules
            errors: Error list to append to
        """
        # Check required field
        if self._check_required_field(field_name, value, rules, errors):
            return  # Field missing, skip other validations

        # Guard clause: skip if value is None
        if value is None:
            return

        # Apply validation rules
        self._validate_field_type(field_name, value, rules, errors)
        self._validate_string_length(field_name, value, rules, errors)
        self._validate_field_pattern(field_name, value, rules, errors)

    def _check_required_field(
        self,
        field_name: str,
        value: t.Any,
        rules: dict[str, t.Any],
        errors: list[str],
    ) -> bool:
        """Check if required field is missing.

        Args:
            field_name: Field name
            value: Field value
            rules: Validation rules
            errors: Error list to append to

        Returns:
            True if field is required and missing, False otherwise
        """
        if not rules.get("required"):
            return False

        is_missing = value is None or (isinstance(value, str) and not value.strip())
        if is_missing:
            errors.append(f"Required field missing: {field_name}")

        return is_missing

    def _validate_field_type(
        self,
        field_name: str,
        value: t.Any,
        rules: dict[str, t.Any],
        errors: list[str],
    ) -> None:
        """Validate field type.

        Args:
            field_name: Field name
            value: Field value
            rules: Validation rules
            errors: Error list to append to
        """
        if "type" not in rules:
            return

        expected_type = rules["type"]
        if not isinstance(value, expected_type):
            errors.append(
                f"Invalid type for {field_name}: expected {expected_type.__name__}"
            )

    def _validate_string_length(
        self,
        field_name: str,
        value: t.Any,
        rules: dict[str, t.Any],
        errors: list[str],
    ) -> None:
        """Validate string length constraints.

        Args:
            field_name: Field name
            value: Field value
            rules: Validation rules
            errors: Error list to append to
        """
        if not isinstance(value, str):
            return

        if "min_length" in rules and len(value) < rules["min_length"]:
            errors.append(f"{field_name} too short (min: {rules['min_length']})")

        if "max_length" in rules and len(value) > rules["max_length"]:
            errors.append(f"{field_name} too long (max: {rules['max_length']})")

    def _validate_field_pattern(
        self,
        field_name: str,
        value: t.Any,
        rules: dict[str, t.Any],
        errors: list[str],
    ) -> None:
        """Validate field against regex pattern.

        Args:
            field_name: Field name
            value: Field value
            rules: Validation rules
            errors: Error list to append to
        """
        if not value or "pattern" not in rules:
            return

        import re

        if not re.match(
            rules["pattern"], str(value)
        ):  # REGEX OK: User-provided validation pattern from schema
            errors.append(f"{field_name} does not match required pattern")


# Singleton instance
_validation_service: FastBlocksValidationService | None = None


def get_validation_service() -> FastBlocksValidationService:
    """Get the singleton FastBlocksValidationService instance."""
    global _validation_service
    if _validation_service is None:
        _validation_service = FastBlocksValidationService()
    return _validation_service


# Decorators for automatic validation


def _extract_template_context(
    args: tuple[t.Any, ...], kwargs: dict[str, t.Any]
) -> tuple[dict[str, t.Any], str]:
    """Extract context and template name from decorator arguments."""
    raw_context: t.Any = kwargs.get("context") or (args[3] if len(args) > 3 else {})
    context: dict[str, t.Any] = raw_context if isinstance(raw_context, dict) else {}
    template = kwargs.get("template") or (args[2] if len(args) > 2 else "unknown")
    return context, str(template)


async def _log_template_validation_errors(
    errors: list[str],
    template: str,
    service: FastBlocksValidationService,
) -> None:
    """Log validation errors if configured."""
    if not (errors and service._config.log_validation_failures):
        return

    with suppress(Exception):
        logger = await depends.get("logger")
        if logger:
            logger.warning(
                f"Template context validation warnings for {template}: {errors}"
            )


def _update_context_in_args(
    args: tuple[t.Any, ...],
    kwargs: dict[str, t.Any],
    sanitized_context: dict[str, t.Any],
) -> tuple[tuple[t.Any, ...], dict[str, t.Any]]:
    """Update args/kwargs with sanitized context."""
    if "context" in kwargs:
        kwargs["context"] = sanitized_context
    elif len(args) > 3:
        args = (*args[:3], sanitized_context, *args[4:])
    return args, kwargs


def validate_template_context(
    strict: bool = False,
) -> t.Callable[
    [t.Callable[..., t.Awaitable[t.Any]]], t.Callable[..., t.Awaitable[t.Any]]
]:
    """Decorator to validate template context before rendering.

    Refactored to reduce cognitive complexity.

    Usage:
        @validate_template_context(strict=False)
        async def render_template(self, request, template, context):
            ...
    """

    def decorator(
        func: t.Callable[..., t.Awaitable[t.Any]],
    ) -> t.Callable[..., t.Awaitable[t.Any]]:
        @functools.wraps(func)
        async def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
            # Extract context and template name
            context, template = _extract_template_context(args, kwargs)

            # Skip validation if context is empty
            if not context:
                return await func(*args, **kwargs)

            # Validate context
            service = get_validation_service()
            (
                _is_valid,
                sanitized_context,
                errors,
            ) = await service.validate_template_context(
                context=context,
                template_name=template,
                strict=strict,
            )

            # Log validation errors if configured
            await _log_template_validation_errors(errors, template, service)

            # Update with sanitized context
            args, kwargs = _update_context_in_args(args, kwargs, sanitized_context)

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _extract_form_data(
    args: tuple[t.Any, ...], kwargs: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Extract form data from decorator arguments."""
    raw_data: t.Any = kwargs.get("form_data") or (args[2] if len(args) > 2 else {})
    return raw_data if isinstance(raw_data, dict) else {}


def _update_form_data(
    args: tuple[t.Any, ...],
    kwargs: dict[str, t.Any],
    sanitized_data: dict[str, t.Any],
) -> tuple[tuple[t.Any, ...], dict[str, t.Any]]:
    """Update args/kwargs with sanitized form data."""
    if "form_data" in kwargs:
        kwargs["form_data"] = sanitized_data
    elif len(args) > 2:
        args = (*args[:2], sanitized_data, *args[3:])
    return args, kwargs


async def _handle_form_validation_errors(
    is_valid: bool,
    errors: list[str],
    service: FastBlocksValidationService,
    strict: bool,
) -> None:
    """Handle form validation errors (logging or raising exception)."""
    if not is_valid and strict:
        from .exceptions import ErrorCategory, FastBlocksException

        raise FastBlocksException(
            message=f"Form validation failed: {'; '.join(errors)}",
            category=ErrorCategory.VALIDATION,
            status_code=400,
        )

    if errors and service._config.log_validation_failures:
        with suppress(Exception):
            logger = await depends.get("logger")
            if logger:
                logger.warning(f"Form validation errors: {errors}")


def validate_form_input(
    schema: dict[str, t.Any] | None = None,
    strict: bool = True,
) -> t.Callable[
    [t.Callable[..., t.Awaitable[t.Any]]], t.Callable[..., t.Awaitable[t.Any]]
]:
    """Decorator to validate and sanitize form input.

    Usage:
        @validate_form_input(schema={"email": {"required": True, "type": str}})
        async def handle_form(self, request, form_data):
            ...
    """

    def decorator(
        func: t.Callable[..., t.Awaitable[t.Any]],
    ) -> t.Callable[..., t.Awaitable[t.Any]]:
        @functools.wraps(func)
        async def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
            # Extract form data
            form_data = _extract_form_data(args, kwargs)

            # Skip validation if no form data
            if not form_data:
                return await func(*args, **kwargs)

            # Validate form data
            service = get_validation_service()
            is_valid, sanitized_data, errors = await service.validate_form_input(
                form_data=form_data,
                schema=schema,
                strict=strict,
            )

            # Handle validation errors
            await _handle_form_validation_errors(is_valid, errors, service, strict)

            # Update with sanitized data
            args, kwargs = _update_form_data(args, kwargs, sanitized_data)

            # Call original function
            return await func(*args, **kwargs)

        return wrapper

    return decorator


def _extract_request_data(
    args: tuple[t.Any, ...], kwargs: dict[str, t.Any]
) -> dict[str, t.Any]:
    """Extract request data from args or kwargs."""
    raw_data: t.Any = kwargs.get("data") or (args[2] if len(args) > 2 else {})
    return raw_data if isinstance(raw_data, dict) else {}


def _update_args_with_data(
    args: tuple[t.Any, ...],
    kwargs: dict[str, t.Any],
    validated_data: dict[str, t.Any],
) -> tuple[tuple[t.Any, ...], dict[str, t.Any]]:
    """Update args/kwargs with validated data."""
    if "data" in kwargs:
        kwargs["data"] = validated_data
    elif len(args) > 2:
        args_list = list(args)
        args_list[2] = validated_data
        args = tuple(args_list)
    return args, kwargs


async def _validate_request(
    service: FastBlocksValidationService,
    request_data: dict[str, t.Any],
    schema: t.Any,
) -> dict[str, t.Any]:
    """Validate request data and raise exception if invalid."""
    is_valid, validated_data, errors = await service.validate_api_request(
        request_data=request_data,
        schema=schema,
    )

    if not is_valid:
        from .exceptions import ErrorCategory, FastBlocksException

        raise FastBlocksException(
            message=f"Request validation failed: {'; '.join(errors)}",
            category=ErrorCategory.VALIDATION,
            status_code=400,
        )

    return validated_data


async def _validate_response(
    service: FastBlocksValidationService,
    response_data: dict[str, t.Any],
    schema: t.Any,
) -> dict[str, t.Any]:
    """Validate response data and log errors if invalid."""
    is_valid, validated_response, errors = await service.validate_api_response(
        response_data=response_data,
        schema=schema,
    )

    if not is_valid:
        with suppress(Exception):
            logger = await depends.get("logger")
            if logger:
                logger.error(f"Response validation failed: {errors}")

    return validated_response


def validate_api_contract(
    request_schema: t.Any = None,
    response_schema: t.Any = None,
) -> t.Callable[
    [t.Callable[..., t.Awaitable[t.Any]]], t.Callable[..., t.Awaitable[t.Any]]
]:
    """Decorator to validate API request/response contracts.

    Usage:
        @validate_api_contract(
            request_schema=UserCreateSchema,
            response_schema=UserSchema
        )
        async def create_user(self, request, data):
            ...
    """

    def decorator(
        func: t.Callable[..., t.Awaitable[t.Any]],
    ) -> t.Callable[..., t.Awaitable[t.Any]]:
        @functools.wraps(func)
        async def wrapper(*args: t.Any, **kwargs: t.Any) -> t.Any:
            service = get_validation_service()

            # Validate request if schema provided
            if request_schema:
                request_data = _extract_request_data(args, kwargs)
                if request_data:
                    validated_data = await _validate_request(
                        service, request_data, request_schema
                    )
                    args, kwargs = _update_args_with_data(args, kwargs, validated_data)

            # Call original function
            result = await func(*args, **kwargs)

            # Validate response if schema provided
            if response_schema and isinstance(result, dict):
                return await _validate_response(service, result, response_schema)

            return result

        return wrapper

    return decorator


async def register_fastblocks_validation() -> bool:
    """Register FastBlocks validation service with ACB.

    Returns:
        True if registration successful, False otherwise
    """
    if not acb_validation_available:
        return False

    try:
        # Initialize validation service
        validation_service = get_validation_service()

        # Register with depends
        depends.set("fastblocks_validation", validation_service)

        return validation_service.available

    except Exception:
        return False


__all__ = [
    "FastBlocksValidationService",
    "ValidationConfig",
    "ValidationType",
    "get_validation_service",
    "validate_template_context",
    "validate_form_input",
    "validate_api_contract",
    "register_fastblocks_validation",
    "acb_validation_available",
]
