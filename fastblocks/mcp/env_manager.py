"""Environment variable management system for FastBlocks configuration."""

import os
import re
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .configuration import ConfigurationSchema, EnvironmentVariable


@dataclass
class EnvironmentValidationResult:
    """Result of environment variable validation."""

    valid: bool = True
    missing_required: list[str] = field(default_factory=list)
    invalid_format: list[str] = field(default_factory=list)
    security_warnings: list[str] = field(default_factory=list)
    recommendations: list[str] = field(default_factory=list)


@dataclass
class EnvironmentTemplate:
    """Template for environment variable generation."""

    name: str
    description: str
    variables: list[EnvironmentVariable] = field(default_factory=list)
    example_values: dict[str, str] = field(default_factory=dict)


class EnvironmentManager:
    """Comprehensive environment variable management for FastBlocks."""

    def __init__(self, base_path: Path | None = None):
        """Initialize environment manager."""
        self.base_path = base_path or Path.cwd()
        self.env_dir = self.base_path / ".fastblocks" / "env"
        self.env_dir.mkdir(parents=True, exist_ok=True)

        # Common validation patterns
        self.validation_patterns = {
            "url": re.compile(
                r"^https?://[^\s/$.?#].[^\s]*$"
            ),  # REGEX OK: URL validation
            "email": re.compile(
                r"^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$"
            ),  # REGEX OK: email validation
            "port": re.compile(  # REGEX OK: port number validation
                r"^([1-9][0-9]{0,3}|[1-5][0-9]{4}|6[0-4][0-9]{3}|65[0-4][0-9]{2}|655[0-2][0-9]|6553[0-5])$"
            ),
            "uuid": re.compile(  # REGEX OK: UUID format validation
                r"^[0-9a-f]{8}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{4}-[0-9a-f]{12}$"
            ),
            "secret_key": re.compile(
                r"^[A-Za-z0-9+/]{32,}$"
            ),  # REGEX OK: secret key format validation
            "path": re.compile(r"^[/~].*"),  # REGEX OK: file path validation
            "boolean": re.compile(
                r"^(true|false|1|0|yes|no|on|off)$", re.IGNORECASE
            ),  # REGEX OK: boolean value validation
            "log_level": re.compile(  # REGEX OK: log level validation
                r"^(DEBUG|INFO|WARNING|ERROR|CRITICAL)$", re.IGNORECASE
            ),
        }

        # Security-sensitive variable patterns
        self.secret_patterns = [
            re.compile(
                r".*secret.*", re.IGNORECASE
            ),  # REGEX OK: detect secret env vars
            re.compile(
                r".*password.*", re.IGNORECASE
            ),  # REGEX OK: detect password env vars
            re.compile(r".*key$", re.IGNORECASE),  # REGEX OK: detect key env vars
            re.compile(r".*token.*", re.IGNORECASE),  # REGEX OK: detect token env vars
            re.compile(
                r".*api_key.*", re.IGNORECASE
            ),  # REGEX OK: detect API key env vars
            re.compile(
                r".*private.*", re.IGNORECASE
            ),  # REGEX OK: detect private env vars
            re.compile(
                r".*credential.*", re.IGNORECASE
            ),  # REGEX OK: detect credential env vars
        ]

    def _check_required_variable(
        self,
        var: EnvironmentVariable,
        current_env: dict[str, str],
        result: EnvironmentValidationResult,
    ) -> None:
        """Check if required variable is present."""
        if (
            var.required
            and var.name not in current_env
            and not var.value
            and not var.default
        ):
            result.missing_required.append(var.name)
            result.valid = False

    def _validate_variable_pattern(
        self,
        var: EnvironmentVariable,
        actual_value: str,
        result: EnvironmentValidationResult,
    ) -> None:
        """Validate variable against its pattern."""
        if var.validator_pattern:
            if not re.match(
                var.validator_pattern, actual_value
            ):  # REGEX OK: custom validator pattern from config
                result.invalid_format.append(
                    f"{var.name}: does not match pattern {var.validator_pattern}"
                )
                result.valid = False

    def validate_environment_variables(
        self,
        variables: list[EnvironmentVariable],
        current_env: dict[str, str] | None = None,
    ) -> EnvironmentValidationResult:
        """Validate environment variables comprehensively."""
        result = EnvironmentValidationResult()
        current_env = current_env or os.environ.copy()

        for var in variables:
            # Check if required variables are present
            self._check_required_variable(var, current_env, result)

            # Get actual value for validation
            actual_value = current_env.get(var.name) or var.value or var.default

            if actual_value:
                # Validate format if pattern is specified
                self._validate_variable_pattern(var, actual_value, result)

                # Check against common patterns
                self._validate_common_patterns(var.name, actual_value, result)

                # Security checks
                self._perform_security_checks(
                    var.name, actual_value, var.secret, result
                )

        # Additional recommendations
        self._generate_recommendations(variables, result)

        return result

    def _validate_common_patterns(
        self, name: str, value: str, result: EnvironmentValidationResult
    ) -> None:
        """Validate against common patterns."""
        name_lower = name.lower()

        self._validate_format_patterns(name, name_lower, value, result)
        self._validate_uuid_pattern(name, name_lower, value, result)
        self._validate_boolean_pattern(name, name_lower, value, result)
        self._validate_log_level_pattern(name, name_lower, value, result)

    def _validate_format_patterns(
        self,
        name: str,
        name_lower: str,
        value: str,
        result: EnvironmentValidationResult,
    ) -> None:
        """Validate URL, email, and port formats."""
        if "url" in name_lower and not self.validation_patterns["url"].match(value):
            result.invalid_format.append(f"{name}: invalid URL format")

        if "email" in name_lower and not self.validation_patterns["email"].match(value):
            result.invalid_format.append(f"{name}: invalid email format")

        if "port" in name_lower and not self.validation_patterns["port"].match(value):
            result.invalid_format.append(f"{name}: invalid port number")

    def _validate_uuid_pattern(
        self,
        name: str,
        name_lower: str,
        value: str,
        result: EnvironmentValidationResult,
    ) -> None:
        """Validate UUID format."""
        if "uuid" in name_lower or "id" in name_lower:
            if not self.validation_patterns["uuid"].match(value):
                result.recommendations.append(f"{name}: consider using UUID format")

    def _validate_boolean_pattern(
        self,
        name: str,
        name_lower: str,
        value: str,
        result: EnvironmentValidationResult,
    ) -> None:
        """Validate boolean values."""
        if (
            "debug" in name_lower
            or "enable" in name_lower
            or name_lower.endswith("_flag")
        ):
            if not self.validation_patterns["boolean"].match(value):
                result.invalid_format.append(
                    f"{name}: should be boolean (true/false, 1/0, yes/no)"
                )

    def _validate_log_level_pattern(
        self,
        name: str,
        name_lower: str,
        value: str,
        result: EnvironmentValidationResult,
    ) -> None:
        """Validate log level values."""
        if "log" in name_lower and "level" in name_lower:
            if not self.validation_patterns["log_level"].match(value):
                result.invalid_format.append(f"{name}: invalid log level")

    def _check_secret_strength(
        self,
        name: str,
        value: str,
        result: EnvironmentValidationResult,
    ) -> None:
        """Check strength of secret values."""
        if len(value) < 16:
            result.security_warnings.append(
                f"{name}: secret appears too short (minimum 16 characters recommended)"
            )

        if value.lower() in (
            "password",
            "secret",
            "key",
            "admin",
            "test",
            "development",
        ):
            result.security_warnings.append(f"{name}: using common/weak secret value")

        if re.match(
            r"^(123|abc|test|dev)", value, re.IGNORECASE
        ):  # REGEX OK: detect weak secrets
            result.security_warnings.append(
                f"{name}: secret appears to use predictable pattern"
            )

    def _perform_security_checks(
        self,
        name: str,
        value: str,
        is_marked_secret: bool,
        result: EnvironmentValidationResult,
    ) -> None:
        """Perform security checks on environment variables."""
        # Check if variable should be marked as secret
        is_potentially_secret = any(
            pattern.match(name) for pattern in self.secret_patterns
        )

        if is_potentially_secret and not is_marked_secret:
            result.security_warnings.append(
                f"{name}: appears to contain sensitive data but not marked as secret"
            )

        # Check for weak secrets
        if is_marked_secret or is_potentially_secret:
            self._check_secret_strength(name, value, result)

        # Check for exposed secrets in non-secret variables
        if not (is_marked_secret or is_potentially_secret):
            if len(value) > 20 and re.match(
                r"^[A-Za-z0-9+/=]+$", value
            ):  # REGEX OK: detect potential base64-encoded secrets
                result.security_warnings.append(
                    f"{name}: value looks like encoded data but not marked as secret"
                )

    def _generate_recommendations(
        self, variables: list[EnvironmentVariable], result: EnvironmentValidationResult
    ) -> None:
        """Generate recommendations for environment variable configuration."""
        var_names = {var.name for var in variables}

        # Check for common missing variables
        common_vars = {
            "DATABASE_URL": "database connection",
            "SECRET_KEY": "application secret",
            "REDIS_URL": "Redis connection",
            "LOG_LEVEL": "logging configuration",
            "DEBUG": "debug mode flag",
        }

        for var_name, description in common_vars.items():
            if not any(var_name in name for name in var_names):
                result.recommendations.append(
                    f"Consider adding {var_name} for {description}"
                )

        # Check for naming consistency
        prefixes = set()
        for var in variables:
            if "_" in var.name:
                prefix = var.name.split("_")[0]
                prefixes.add(prefix)

        if len(prefixes) > 3:
            result.recommendations.append(
                "Consider using consistent prefixes for related variables"
            )

    def _generate_file_header(self, template: str | None) -> list[str]:
        """Generate .env file header with documentation."""
        return [
            "# FastBlocks Environment Configuration",
            "# Generated by FastBlocks Configuration Manager",
            f"# Template: {template or 'custom'}",
            "",
            "# IMPORTANT: This file contains sensitive information",
            "# - Do not commit this file to version control",
            "# - Copy to .env and customize for your environment",
            "# - Use .env.example for version control",
            "",
        ]

    def _generate_variable_value(
        self, var: EnvironmentVariable, include_examples: bool
    ) -> str:
        """Generate value for an environment variable."""
        if var.secret and include_examples:
            if var.value:
                return "***REDACTED***"
            return f"<your-{var.name.lower().replace('_', '-')}>"
        return var.value or var.default or ""

    def _generate_variable_lines(
        self, var: EnvironmentVariable, include_docs: bool, include_examples: bool
    ) -> list[str]:
        """Generate lines for a single environment variable."""
        lines = []

        # Add description
        if include_docs and var.description:
            lines.append(f"# {var.description}")

        # Add requirement indicator
        if include_docs:
            requirement = "REQUIRED" if var.required else "OPTIONAL"
            lines.append(f"# {requirement}")

        # Add validation info
        if include_docs and var.validator_pattern:
            lines.append(f"# Format: {var.validator_pattern}")

        # Add variable with value
        value = self._generate_variable_value(var, include_examples)
        lines.extend((f"{var.name}={value}", ""))

        return lines

    def generate_environment_file(
        self,
        variables: list[EnvironmentVariable],
        output_path: Path | None = None,
        template: str | None = None,
        include_examples: bool = True,
        include_docs: bool = True,
    ) -> Path:
        """Generate comprehensive .env file."""
        if not output_path:
            output_path = self.base_path / ".env"

        lines = []

        if include_docs:
            lines.extend(self._generate_file_header(template))

        # Group variables by prefix
        grouped_vars = self._group_variables_by_prefix(variables)

        for prefix, prefix_vars in grouped_vars.items():
            if include_docs:
                lines.extend((f"# {prefix.upper()} Configuration", ""))

            for var in prefix_vars:
                lines.extend(
                    self._generate_variable_lines(var, include_docs, include_examples)
                )

        # Write file
        with output_path.open("w") as f:
            f.write("\n".join(lines))

        return output_path

    def generate_environment_example(
        self, variables: list[EnvironmentVariable], output_path: Path | None = None
    ) -> Path:
        """Generate .env.example file for version control."""
        if not output_path:
            output_path = self.base_path / ".env.example"

        # Create example with placeholder values
        example_variables = []
        for var in variables:
            example_var = EnvironmentVariable(
                name=var.name,
                value=self._generate_example_value(var),
                required=var.required,
                description=var.description,
                secret=var.secret,
                default=var.default,
                validator_pattern=var.validator_pattern,
            )
            example_variables.append(example_var)

        return self.generate_environment_file(
            example_variables, output_path, include_examples=True, include_docs=True
        )

    def _generate_example_value(self, var: EnvironmentVariable) -> str:
        """Generate example value for environment variable."""
        name_lower = var.name.lower()

        if var.secret:
            return f"your-{var.name.lower().replace('_', '-')}-here"

        if "url" in name_lower:
            if "database" in name_lower:
                return "postgresql://user:password@localhost:5432/dbname"
            elif "redis" in name_lower:
                return "redis://localhost:6379/0"

            return "https://example.com"

        if "port" in name_lower:
            return "8000"

        if "email" in name_lower:
            return "admin@example.com"

        if "debug" in name_lower or name_lower.endswith("_flag"):
            return "false"

        if "log" in name_lower and "level" in name_lower:
            return "INFO"

        if "path" in name_lower:
            return "/path/to/directory"

        return f"example-{var.name.lower().replace('_', '-')}"

    def _group_variables_by_prefix(
        self, variables: list[EnvironmentVariable]
    ) -> dict[str, list[EnvironmentVariable]]:
        """Group variables by common prefix."""
        grouped: dict[str, list[EnvironmentVariable]] = {}

        for var in variables:
            # Determine prefix
            if "_" in var.name:
                prefix = var.name.split("_")[0]
            else:
                prefix = "general"

            if prefix not in grouped:
                grouped[prefix] = []
            grouped[prefix].append(var)

        # Sort variables within each group
        for prefix in grouped:
            grouped[prefix].sort(key=lambda v: (not v.required, v.name))

        return grouped

    def _parse_env_line(self, line: str) -> tuple[str, str] | None:
        """Parse a single environment variable line.

        Args:
            line: Line to parse

        Returns:
            Tuple of (key, value) or None if line should be skipped
        """
        line = line.strip()

        # Skip comments and empty lines
        if not line or line.startswith("#"):
            return None

        # Parse variable assignment
        if "=" not in line:
            return None

        key, value = line.split("=", 1)
        key = key.strip()
        value = value.strip()

        # Remove quotes if present
        if (value.startswith('"') and value.endswith('"')) or (
            value.startswith("'") and value.endswith("'")
        ):
            value = value[1:-1]

        return key, value

    def load_environment_from_file(self, env_file: Path) -> dict[str, str]:
        """Load environment variables from .env file."""
        env_vars: dict[str, str] = {}

        if not env_file.exists():
            return env_vars

        with env_file.open() as f:
            for line in f:
                parsed = self._parse_env_line(line)
                if parsed:
                    key, value = parsed
                    env_vars[key] = value

        return env_vars

    def sync_environment_variables(
        self, variables: list[EnvironmentVariable], env_file: Path | None = None
    ) -> dict[str, Any]:
        """Sync environment variables with .env file."""
        env_file = env_file or (self.base_path / ".env")

        # Load existing environment
        existing_env = (
            self.load_environment_from_file(env_file) if env_file.exists() else {}
        )

        # Update variables with values from file
        updated_count = 0
        new_count = 0

        for var in variables:
            if var.name in existing_env:
                if var.value != existing_env[var.name]:
                    var.value = existing_env[var.name]
                    updated_count += 1
            else:
                new_count += 1

        return {
            "updated": updated_count,
            "new": new_count,
            "total": len(variables),
            "file_exists": env_file.exists() if env_file else False,
        }

    def generate_environment_templates(self) -> dict[str, EnvironmentTemplate]:
        """Generate standard environment templates."""
        templates = {}

        # Development template
        dev_vars = [
            EnvironmentVariable("DEBUG", "true", False, "Enable debug mode"),
            EnvironmentVariable("LOG_LEVEL", "DEBUG", False, "Logging level"),
            EnvironmentVariable(
                "SECRET_KEY", None, True, "Application secret key", True
            ),
            EnvironmentVariable(
                "DATABASE_URL", "sqlite:///./dev.db", False, "Database connection"
            ),
            EnvironmentVariable(
                "REDIS_URL", "redis://localhost:6379/0", False, "Redis connection"
            ),
        ]
        templates["development"] = EnvironmentTemplate(
            "development", "Development environment configuration", dev_vars
        )

        # Production template
        prod_vars = [
            EnvironmentVariable("DEBUG", "false", True, "Debug mode (should be false)"),
            EnvironmentVariable("LOG_LEVEL", "WARNING", True, "Logging level"),
            EnvironmentVariable(
                "SECRET_KEY", None, True, "Application secret key", True
            ),
            EnvironmentVariable(
                "DATABASE_URL", None, True, "Database connection", True
            ),
            EnvironmentVariable("REDIS_URL", None, False, "Redis connection"),
            EnvironmentVariable("ALLOWED_HOSTS", "*", True, "Allowed hosts"),
            EnvironmentVariable("HTTPS_ONLY", "true", True, "Force HTTPS"),
        ]
        templates["production"] = EnvironmentTemplate(
            "production", "Production environment configuration", prod_vars
        )

        # Testing template
        test_vars = [
            EnvironmentVariable("DEBUG", "true", True, "Enable debug mode"),
            EnvironmentVariable("LOG_LEVEL", "DEBUG", False, "Logging level"),
            EnvironmentVariable(
                "SECRET_KEY",
                "test-secret-key-do-not-use-in-production",
                True,
                "Test secret key",
            ),
            EnvironmentVariable(
                "DATABASE_URL", "sqlite:///:memory:", True, "In-memory test database"
            ),
            EnvironmentVariable("TESTING", "true", True, "Testing mode flag"),
        ]
        templates["testing"] = EnvironmentTemplate(
            "testing", "Testing environment configuration", test_vars
        )

        return templates

    def extract_variables_from_configuration(
        self, config: ConfigurationSchema
    ) -> list[EnvironmentVariable]:
        """Extract all environment variables from configuration."""
        all_variables = []

        # Add global environment variables
        all_variables.extend(config.global_environment)

        # Add adapter environment variables
        for adapter_config in config.adapters.values():
            if adapter_config.enabled:
                all_variables.extend(adapter_config.environment_variables)

        # Remove duplicates (by name)
        seen_names = set()
        unique_variables = []
        for var in all_variables:
            if var.name not in seen_names:
                unique_variables.append(var)
                seen_names.add(var.name)

        return unique_variables

    def audit_environment_security(
        self, variables: list[EnvironmentVariable]
    ) -> dict[str, list[str]]:
        """Perform security audit of environment variables."""
        audit_results: dict[str, Any] = {
            "critical": [],
            "high": [],
            "medium": [],
            "low": [],
            "info": [],
        }

        for var in variables:
            self._audit_secret_marking(var, audit_results)
            self._audit_secret_strength(var, audit_results)
            self._audit_required_values(var, audit_results)
            self._audit_format_validation(var, audit_results)
            self._audit_best_practices(var, audit_results)

        return audit_results

    def _audit_secret_marking(
        self, var: EnvironmentVariable, audit_results: dict[str, list[str]]
    ) -> None:
        """Audit if secrets are properly marked."""
        is_secret_name = any(
            pattern.match(var.name) for pattern in self.secret_patterns
        )
        if is_secret_name and not var.secret:
            audit_results["critical"].append(
                f"{var.name}: Contains sensitive data but not marked as secret"
            )

    def _audit_secret_strength(
        self, var: EnvironmentVariable, audit_results: dict[str, list[str]]
    ) -> None:
        """Audit secret value strength."""
        if var.secret and var.value:
            if len(var.value) < 16:
                audit_results["high"].append(
                    f"{var.name}: Secret is too short (< 16 characters)"
                )
            if var.value.lower() in ("password", "secret", "admin", "test"):
                audit_results["high"].append(
                    f"{var.name}: Using weak/common secret value"
                )

    def _audit_required_values(
        self, var: EnvironmentVariable, audit_results: dict[str, list[str]]
    ) -> None:
        """Audit if required variables have values."""
        if var.required and not var.value and not var.default:
            audit_results["medium"].append(
                f"{var.name}: Required variable has no value or default"
            )

    def _audit_format_validation(
        self, var: EnvironmentVariable, audit_results: dict[str, list[str]]
    ) -> None:
        """Audit format validation patterns."""
        if var.validator_pattern and var.value:
            if not re.match(
                var.validator_pattern, var.value
            ):  # REGEX OK: custom validator pattern from config
                audit_results["low"].append(
                    f"{var.name}: Value doesn't match expected pattern"
                )

    def _audit_best_practices(
        self, var: EnvironmentVariable, audit_results: dict[str, list[str]]
    ) -> None:
        """Audit best practice compliance."""
        if not var.description:
            audit_results["info"].append(f"{var.name}: Missing description")
