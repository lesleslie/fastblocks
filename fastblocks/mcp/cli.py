"""Command-line interface for FastBlocks MCP adapter management."""

import asyncio
import json
import typing as t
from pathlib import Path

import click

from .config_audit import ConfigurationAuditor
from .config_cli import config_cli
from .config_health import ConfigurationHealthChecker
from .config_migration import ConfigurationMigrationManager
from .configuration import ConfigurationManager
from .env_manager import EnvironmentManager
from .health import HealthCheckSystem
from .registry import AdapterRegistry

# Audit output formatting helpers
_SEVERITY_COLORS = {
    "critical": "red",
    "high": "red",
    "medium": "yellow",
    "low": "white",
    "info": "cyan",
}

# Health check formatting helpers
_HEALTH_STATUS_COLORS = {
    "healthy": "green",
    "warning": "yellow",
    "error": "red",
}


def _display_health_result_summary(name: str, result: t.Any) -> None:
    """Display a single health check result in summary format."""
    status_color = _HEALTH_STATUS_COLORS.get(result.status, "white")
    click.echo(f"{name:<20} ", nl=False)
    click.secho(f"{result.status.upper():<8}", fg=status_color, nl=False)
    click.echo(f" {result.message}")


def _display_health_result_detail(adapter_name: str, result: t.Any) -> None:
    """Display a single health check result with full details."""
    status_color = _HEALTH_STATUS_COLORS.get(result.status, "white")

    click.echo(f"Health Check: {adapter_name}")
    click.secho(f"Status: {result.status.upper()}", fg=status_color)
    click.echo(f"Message: {result.message}")
    click.echo(f"Duration: {result.duration_ms:.2f}ms")

    if result.details:
        click.echo("Details:")
        for key, value in result.details.items():
            if isinstance(value, list):
                click.echo(f"  {key}: {', '.join(value) if value else 'None'}")
            else:
                click.echo(f"  {key}: {value}")


def _display_system_health_summary(summary: dict[str, t.Any]) -> None:
    """Display overall system health summary."""
    total = summary["total_adapters"]
    click.echo("System Health Summary:")
    click.echo(f"Total Adapters: {total}")
    if total > 0:
        click.secho(f"Healthy: {summary['healthy_adapters']}", fg="green")
        click.secho(f"Warnings: {summary['warning_adapters']}", fg="yellow")
        click.secho(f"Errors: {summary['error_adapters']}", fg="red")
        click.echo(f"Unknown: {summary['unknown_adapters']}")


def _display_migration_compatibility(
    compatibility: dict[str, t.Any], target_version: str
) -> None:
    """Display migration compatibility information."""
    click.echo(f"Migration from {compatibility['current_version']} to {target_version}")
    click.echo(f"Steps: {' -> '.join(compatibility['migration_path'])}")

    if compatibility["warnings"]:
        click.echo("\nWarnings:")
        for warning in compatibility["warnings"]:
            click.echo(f"  - {warning}")


def _display_migration_incompatibility(compatibility: dict[str, t.Any]) -> None:
    """Display migration incompatibility errors."""
    click.echo("Migration not possible:", err=True)
    for warning in compatibility["warnings"]:
        click.echo(f"  - {warning}", err=True)


def _display_migration_success(result: t.Any) -> None:
    """Display successful migration results."""
    click.secho("✓ Migration completed successfully", fg="green")
    click.echo(f"Steps applied: {', '.join(result.steps_applied)}")
    if result.warnings:
        click.echo("Warnings:")
        for warning in result.warnings:
            click.secho(f"  - {warning}", fg="yellow")


def _display_migration_failure(result: t.Any) -> None:
    """Display migration failure errors."""
    click.secho("✗ Migration failed", fg="red")
    for error in result.errors:
        click.echo(f"  - {error}")


def _format_finding_for_json(finding: t.Any) -> dict[str, t.Any]:
    """Format a single finding for JSON output."""
    return {
        "id": finding.id,
        "category": finding.category.value,
        "severity": finding.severity.value,
        "title": finding.title,
        "description": finding.description,
        "recommendation": finding.recommendation,
        "affected_items": finding.affected_items,
    }


def _write_json_audit_report(report: t.Any, output_path: str | None) -> None:
    """Write audit report in JSON format."""
    import json

    output_data = {
        "configuration_name": report.configuration_name,
        "profile": report.profile,
        "score": report.score,
        "summary": report.summary,
        "findings": [_format_finding_for_json(f) for f in report.findings],
    }

    if output_path:
        with open(output_path, "w") as f:
            json.dump(output_data, f, indent=2)
    else:
        click.echo(json.dumps(output_data, indent=2))


def _display_audit_finding(finding: t.Any) -> None:
    """Display a single audit finding to console."""
    severity_color = _SEVERITY_COLORS.get(finding.severity.value, "white")

    click.secho(
        f"\n[{finding.severity.value.upper()}] {finding.title}",
        fg=severity_color,
    )
    click.echo(f"  {finding.description}")
    click.echo(f"  Recommendation: {finding.recommendation}")
    if finding.affected_items:
        click.echo(f"  Affected: {', '.join(finding.affected_items)}")


def _display_text_audit_report(report: t.Any) -> None:
    """Display audit report in text format to console."""
    click.echo(f"Configuration Audit Report: {report.configuration_name}")
    click.echo(f"Profile: {report.profile}")
    click.echo(f"Score: {report.score}/100")
    click.echo(f"Total Findings: {report.summary['total_findings']}")

    if report.findings:
        click.echo("\nFindings:")
        for finding in report.findings:
            _display_audit_finding(finding)

    if report.recommendations:
        click.echo("\nRecommendations:")
        for rec in report.recommendations:
            click.echo(f"  • {rec}")


def _write_text_audit_report(report: t.Any, output_path: str) -> None:
    """Write audit report in text format to file."""
    with open(output_path, "w") as f:
        f.write("Configuration Audit Report\n")
        f.write("========================\n\n")
        f.write(f"Configuration: {report.configuration_name}\n")
        f.write(f"Profile: {report.profile}\n")
        f.write(f"Score: {report.score}/100\n\n")


async def get_registry_and_health() -> tuple[AdapterRegistry, HealthCheckSystem]:
    """Get initialized registry and health check system."""
    registry = AdapterRegistry()
    await registry.initialize()
    health = HealthCheckSystem(registry)
    return registry, health


@click.group()
def cli() -> None:
    """FastBlocks MCP Adapter Management CLI."""
    pass


# Add configuration management commands
cli.add_command(config_cli, name="config")


@cli.command()
@click.option("--format", type=click.Choice(["json", "table"]), default="table")
def list_adapters(format: str) -> None:
    """List all available adapters."""

    async def _list() -> None:
        registry, _ = await get_registry_and_health()
        adapters = await registry.list_available_adapters()

        if format == "json":
            output = {name: info.to_dict() for name, info in adapters.items()}
            click.echo(json.dumps(output, indent=2))
        else:
            click.echo("Available Adapters:")
            click.echo("-" * 50)
            for name, info in adapters.items():
                status_color = "green" if info.module_status == "stable" else "yellow"
                click.echo(f"  {name:<20} {info.category:<12} ", nl=False)
                click.secho(info.module_status, fg=status_color)
                if info.description:
                    click.echo(f"    {info.description}")

    asyncio.run(_list())


@cli.command()
@click.option("--category", help="Filter by category")
def list_categories(category: str | None = None) -> None:
    """List adapter categories."""

    async def _list_categories() -> None:
        registry, _ = await get_registry_and_health()

        if category:
            adapters = await registry.get_adapters_by_category(category)
            click.echo(f"Adapters in category '{category}':")
            for adapter in adapters:
                click.echo(f"  - {adapter.name}")
        else:
            categories = await registry.get_categories()
            click.echo("Available Categories:")
            for cat in sorted(categories):
                click.echo(f"  - {cat}")

    asyncio.run(_list_categories())


@cli.command()
@click.argument("adapter_name")
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
def inspect(adapter_name: str, format: str) -> None:
    """Inspect a specific adapter."""

    async def _inspect() -> None:
        registry, _ = await get_registry_and_health()
        info = await registry.get_adapter_info(adapter_name)

        if not info:
            click.echo(f"Adapter '{adapter_name}' not found", err=True)
            return

        if format == "json":
            click.echo(json.dumps(info.to_dict(), indent=2))
        else:
            click.echo(f"Adapter: {info.name}")
            click.echo(f"Class: {info.class_name}")
            click.echo(f"Module: {info.module_path}")
            click.echo(f"Category: {info.category}")
            click.echo(f"Status: {info.module_status}")
            click.echo(f"ID: {info.module_id}")
            if info.description:
                click.echo(f"Description: {info.description}")
            if info.protocols:
                click.echo(f"Protocols: {', '.join(info.protocols)}")
            if info.settings_class:
                click.echo(f"Settings Class: {info.settings_class}")

    asyncio.run(_inspect())


@cli.command()
@click.argument("adapter_name")
def validate(adapter_name: str) -> None:
    """Validate an adapter configuration."""

    async def _validate() -> None:
        registry, _ = await get_registry_and_health()
        result = await registry.validate_adapter(adapter_name)

        if result["valid"]:
            click.secho(f"✓ Adapter '{adapter_name}' is valid", fg="green")
        else:
            click.secho(f"✗ Adapter '{adapter_name}' has issues", fg="red")

        if result["errors"]:
            click.echo("Errors:")
            for error in result["errors"]:
                click.secho(f"  - {error}", fg="red")

        if result["warnings"]:
            click.echo("Warnings:")
            for warning in result["warnings"]:
                click.secho(f"  - {warning}", fg="yellow")

    asyncio.run(_validate())


async def _display_all_adapters_health(health_system: t.Any, format: str) -> None:
    """Display health results for all adapters."""
    results = await health_system.check_all_adapters()
    if format == "json":
        output = {name: result.to_dict() for name, result in results.items()}
        click.echo(json.dumps(output, indent=2))
    else:
        click.echo("Health Check Results:")
        click.echo("-" * 50)
        for name, result in results.items():
            _display_health_result_summary(name, result)


async def _display_single_adapter_health(
    health_system: t.Any, adapter_name: str, format: str
) -> None:
    """Display health result for a single adapter."""
    result = await health_system.check_adapter_health(adapter_name)
    if format == "json":
        click.echo(json.dumps(result.to_dict(), indent=2))
    else:
        _display_health_result_detail(adapter_name, result)


async def _display_system_health_summary_cli(health_system: t.Any, format: str) -> None:
    """Display system health summary."""
    summary = health_system.get_system_health_summary()
    if format == "json":
        click.echo(json.dumps(summary, indent=2))
    else:
        _display_system_health_summary(summary)


@cli.command()
@click.argument("adapter_name", required=False)
@click.option("--all", is_flag=True, help="Check all adapters")
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
def health(
    adapter_name: str | None = None, all: bool = False, format: str = "text"
) -> None:
    """Perform health checks on adapters."""

    async def _health() -> None:
        _registry, health_system = await get_registry_and_health()

        if all:
            await _display_all_adapters_health(health_system, format)
        elif adapter_name:
            await _display_single_adapter_health(health_system, adapter_name, format)
        else:
            await _display_system_health_summary_cli(health_system, format)

    asyncio.run(_health())


@cli.command()
def statistics() -> None:
    """Show adapter statistics."""

    async def _stats() -> None:
        registry, _ = await get_registry_and_health()
        stats = await registry.get_adapter_statistics()

        click.echo("Adapter Statistics:")
        click.echo(f"Total Available: {stats['total_available']}")
        click.echo(f"Total Active: {stats['total_active']}")
        click.echo(f"Categories: {stats['total_categories']}")

        click.echo("\nBy Category:")
        for category, info in stats["categories"].items():
            click.echo(f"  {category}: {info['total']} adapters")

        click.echo("\nBy Status:")
        for status, count in stats["status_breakdown"].items():
            click.echo(f"  {status}: {count}")

        if stats["active_adapters"]:
            click.echo(f"\nActive Adapters: {', '.join(stats['active_adapters'])}")

    asyncio.run(_stats())


@cli.command()
@click.option(
    "--auto-register", is_flag=True, help="Automatically register all adapters"
)
def register(auto_register: bool = False) -> None:
    """Register adapters with the system."""

    async def _register() -> None:
        registry, _ = await get_registry_and_health()

        if auto_register:
            results = await registry.auto_register_available_adapters()

            success_count = sum(1 for success in results.values() if success)
            total_count = len(results)

            click.echo(
                f"Auto-registration completed: {success_count}/{total_count} successful"
            )

            for name, success in results.items():
                status = "✓" if success else "✗"
                color = "green" if success else "red"
                click.secho(f"  {status} {name}", fg=color)
        else:
            click.echo("Use --auto-register to register all available adapters")

    asyncio.run(_register())


@cli.command()
@click.argument("config_file")
@click.option("--output", "-o", help="Output report file")
@click.option("--format", type=click.Choice(["json", "text"]), default="text")
def audit(config_file: str, output: str | None, format: str) -> None:
    """Audit configuration for security and compliance."""

    async def _audit() -> None:
        registry = AdapterRegistry()
        env_manager = EnvironmentManager()
        auditor = ConfigurationAuditor(env_manager)

        await registry.initialize()

        config_manager = ConfigurationManager(registry)
        await config_manager.initialize()

        try:
            config = await config_manager.load_configuration(config_file)
            report = await auditor.audit_configuration(config)

            if format == "json":
                _write_json_audit_report(report, output)
            else:
                _display_text_audit_report(report)
                if output:
                    _write_text_audit_report(report, output)

        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    asyncio.run(_audit())


@cli.command()
@click.argument("config_file")
@click.argument("target_version")
@click.option(
    "--backup/--no-backup", default=True, help="Create backup before migration"
)
@click.option("--output", "-o", help="Output file for migrated configuration")
def migrate(
    config_file: str, target_version: str, backup: bool, output: str | None
) -> None:
    """Migrate configuration to target version."""

    async def _migrate() -> None:
        migration_manager = ConfigurationMigrationManager()

        config_path = Path(config_file)
        if not config_path.exists():
            click.echo(f"Configuration file not found: {config_file}", err=True)
            return

        # Validate migration compatibility
        compatibility = await migration_manager.validate_migration_compatibility(
            config_path, target_version
        )

        if not compatibility["compatible"]:
            _display_migration_incompatibility(compatibility)
            return

        _display_migration_compatibility(compatibility, target_version)

        if not click.confirm("Continue with migration?"):
            return

        # Create backup if requested
        if backup:
            backup_path = await migration_manager.create_migration_backup(
                config_path, target_version
            )
            click.echo(f"Backup created: {backup_path}")

        # Perform migration
        result = await migration_manager.migrate_configuration_file(
            config_path, target_version, Path(output) if output else None
        )

        if result.success:
            _display_migration_success(result)
        else:
            _display_migration_failure(result)

    asyncio.run(_migrate())


def _parse_test_types(test_types: str | None) -> list[t.Any] | None:
    """Parse comma-separated test types into a list."""
    if not test_types:
        return None

    from .config_health import ConfigurationTestType

    return [
        ConfigurationTestType(test_type.strip()) for test_type in test_types.split(",")
    ]


def _display_health_summary(report: t.Any, config_file: str) -> None:
    """Display health check summary information."""
    status_color = {"valid": "green", "warning": "yellow", "error": "red"}.get(
        report.overall_status.value, "white"
    )

    click.echo(f"Configuration Health Check: {config_file}")
    click.secho(
        f"Overall Status: {report.overall_status.value.upper()}",
        fg=status_color,
    )
    click.echo(f"Total Tests: {report.summary['total_tests']}")
    click.echo(f"Passed: {report.summary['passed_tests']}")
    click.echo(f"Failed: {report.summary['failed_tests']}")
    click.echo(f"Pass Rate: {report.summary['pass_rate']:.1f}%")


def _display_failed_tests(failed_tests: list[t.Any]) -> None:
    """Display failed test details."""
    if not failed_tests:
        return

    click.echo(f"\nFailed Tests ({len(failed_tests)}):")
    for test in failed_tests:
        severity_color = {
            "critical": "red",
            "high": "red",
            "medium": "yellow",
            "low": "white",
        }.get(test.severity.value, "white")

        click.secho(
            f"  [{test.severity.value.upper()}] {test.test_name}",
            fg=severity_color,
        )
        click.echo(f"    {test.message}")


def _display_recommendations(recommendations: list[str]) -> None:
    """Display health check recommendations."""
    if not recommendations:
        return

    click.echo("\nRecommendations:")
    for rec in recommendations:
        click.echo(f"  • {rec}")


async def _save_health_report_if_requested(
    health_checker: t.Any, report: t.Any, output: str | None
) -> None:
    """Save health report to file if output path is provided."""
    if output:
        await health_checker._save_health_report(report, Path(output))
        click.echo(f"\nReport saved to: {output}")


@cli.command()
@click.argument("config_file")
@click.option("--test-types", help="Comma-separated test types to run")
@click.option("--output", "-o", help="Output report file")
def health_check(config_file: str, test_types: str | None, output: str | None) -> None:
    """Run comprehensive health check on configuration."""

    async def _health_check() -> None:
        registry = AdapterRegistry()
        env_manager = EnvironmentManager()
        health_checker = ConfigurationHealthChecker(registry, env_manager)

        await registry.initialize()

        config_manager = ConfigurationManager(registry)
        await config_manager.initialize()

        try:
            config = await config_manager.load_configuration(config_file)

            # Parse test types and run health check
            test_type_list = _parse_test_types(test_types)
            report = await health_checker.run_comprehensive_health_check(
                config, test_type_list
            )

            # Display results
            _display_health_summary(report, config_file)

            # Show failed tests
            failed_tests = [r for r in report.test_results if not r.passed]
            _display_failed_tests(failed_tests)

            # Show recommendations
            _display_recommendations(report.recommendations)

            # Save report if requested
            await _save_health_report_if_requested(health_checker, report, output)

        except Exception as e:
            click.echo(f"Error: {e}", err=True)

    asyncio.run(_health_check())


if __name__ == "__main__":
    cli()
