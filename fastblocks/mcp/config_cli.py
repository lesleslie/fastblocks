"""Interactive CLI for FastBlocks adapter configuration management."""

import asyncio
import json
import os
import sys
import typing as t
from pathlib import Path
from typing import Any

import click
from acb.console import Console
from acb.depends import depends
from mcp_common.ui import ServerPanels
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .configuration import (
    ConfigurationManager,
    ConfigurationProfile,
    ConfigurationSchema,
    ConfigurationStatus,
    ConfigurationValidationResult,
    EnvironmentVariable,
)
from .health import HealthCheckSystem
from .registry import AdapterRegistry

console = depends.get_sync(Console)


class InteractiveConfigurationCLI:
    """Interactive CLI for adapter configuration."""

    def __init__(self) -> None:
        """Initialize the interactive CLI."""
        self.registry = AdapterRegistry()
        self.health = HealthCheckSystem(self.registry)
        self.config_manager = ConfigurationManager(self.registry)

    async def initialize(self) -> None:
        """Initialize all systems."""
        await self.registry.initialize()
        await self.config_manager.initialize()

    async def run_configuration_wizard(self) -> ConfigurationSchema:
        """Run the interactive configuration wizard."""
        console.print(
            Panel.fit(
                "[bold blue]FastBlocks Adapter Configuration Wizard[/bold blue]\n"
                "This wizard will help you configure FastBlocks adapters for your project.",
                title="Welcome",
            )
        )

        # Step 1: Select profile
        profile = self._select_profile()

        # Step 2: Select adapters
        selected_adapters = await self._select_adapters()

        # Step 3: Configure selected adapters
        config = await self.config_manager.create_configuration(
            profile=profile, adapters=selected_adapters
        )

        # Step 4: Configure each adapter
        for adapter_name in selected_adapters:
            await self._configure_adapter_interactive(config, adapter_name)

        # Step 5: Configure global settings
        await self._configure_global_settings(config)

        # Step 6: Validate configuration
        console.print("\n[yellow]Validating configuration...[/yellow]")
        validation_result = await self.config_manager.validate_configuration(config)
        self._display_validation_result(validation_result)

        if validation_result.status == ConfigurationStatus.ERROR:
            if not Confirm.ask("Configuration has errors. Continue anyway?"):
                console.print("[red]Configuration cancelled.[/red]")
                sys.exit(1)

        # Step 7: Save configuration
        config_name = Prompt.ask(
            "Configuration name", default=f"{profile.value}_config"
        )

        config_file = await self.config_manager.save_configuration(config, config_name)
        console.print(f"\n[green]✓[/green] Configuration saved to: {config_file}")

        # Step 8: Generate environment file
        if Confirm.ask("Generate .env file?", default=True):
            env_file = await self.config_manager.generate_environment_file(config)
            console.print(f"[green]✓[/green] Environment file created: {env_file}")

        # Step 9: Create backup
        if Confirm.ask("Create backup?", default=True):
            backup_description = Prompt.ask(
                "Backup description", default="Initial configuration"
            )
            backup = await self.config_manager.backup_configuration(
                config, config_name, backup_description
            )
            console.print(f"[green]✓[/green] Backup created: {backup.id}")

        return config

    def _select_profile(self) -> ConfigurationProfile:
        """Interactive profile selection."""
        console.print("\n[bold]Select deployment profile:[/bold]")

        profiles = {
            "1": (
                ConfigurationProfile.DEVELOPMENT,
                "Development - Debug enabled, relaxed security",
            ),
            "2": (
                ConfigurationProfile.STAGING,
                "Staging - Production-like with debug options",
            ),
            "3": (
                ConfigurationProfile.PRODUCTION,
                "Production - Optimized for performance and security",
            ),
        }

        for key, (profile, description) in profiles.items():
            console.print(
                f"  {key}. [cyan]{profile.value.title()}[/cyan] - {description}"
            )

        choice = Prompt.ask(
            "Choose profile", choices=list(profiles.keys()), default="1"
        )

        selected_profile, _ = profiles[choice]
        console.print(
            f"[green]✓[/green] Selected profile: [cyan]{selected_profile.value.title()}[/cyan]"
        )
        return selected_profile

    def _group_adapters_by_category(
        self, available_adapters: dict[str, Any]
    ) -> dict[str, list[tuple[str, Any]]]:
        """Group adapters by category.

        Args:
            available_adapters: Dict of adapter name -> adapter info

        Returns:
            Dict of category -> list of (adapter_name, adapter_info)
        """
        categories: dict[str, list[tuple[str, Any]]] = {}

        for adapter_name, adapter_info in available_adapters.items():
            category = adapter_info.category
            if category not in categories:
                categories[category] = []
            categories[category].append((adapter_name, adapter_info))

        return categories

    def _display_adapter_choices(
        self, categories: dict[str, list[tuple[str, Any]]]
    ) -> dict[str, str]:
        """Display adapters by category and build choice mapping.

        Args:
            categories: Dict of category -> list of (adapter_name, adapter_info)

        Returns:
            Dict mapping choice number to adapter name
        """
        adapter_choices = {}
        choice_num = 1

        for category, adapters in sorted(categories.items()):
            console.print(f"\n[bold yellow]{category.title()}:[/bold yellow]")
            for adapter_name, adapter_info in sorted(adapters):
                status_color = (
                    "green" if adapter_info.module_status == "stable" else "yellow"
                )
                console.print(
                    f"  {choice_num:2d}. [cyan]{adapter_name:<20}[/cyan] "
                    f"[{status_color}]{adapter_info.module_status:<12}[/{status_color}] "
                    f"{adapter_info.description or 'No description'}"
                )
                adapter_choices[str(choice_num)] = adapter_name
                choice_num += 1

        return adapter_choices

    def _get_recommended_adapters(
        self, available_adapters: dict[str, Any]
    ) -> list[str]:
        """Get recommended default adapters.

        Args:
            available_adapters: Dict of available adapters

        Returns:
            List of recommended adapter names
        """
        recommended = ["app", "templates", "routes"]
        selected = [name for name in recommended if name in available_adapters]
        console.print(
            f"[green]✓[/green] Using recommended adapters: {', '.join(selected)}"
        )
        return selected

    def _parse_adapter_selection(
        self, selection: str, adapter_choices: dict[str, str]
    ) -> list[str]:
        """Parse user's adapter selection.

        Args:
            selection: Comma-separated choice numbers
            adapter_choices: Dict mapping choice number to adapter name

        Returns:
            List of selected adapter names
        """
        selected_adapters = []

        for choice in selection.split(","):
            choice = choice.strip()
            if choice in adapter_choices:
                selected_adapters.append(adapter_choices[choice])
            else:
                console.print(f"[red]Warning:[/red] Invalid choice '{choice}' ignored")

        # Print result
        if selected_adapters:
            console.print(
                f"[green]✓[/green] Selected adapters: {', '.join(selected_adapters)}"
            )
        else:
            console.print("[red]No adapters selected![/red]")

        return selected_adapters

    async def _select_adapters(self) -> list[str]:
        """Interactive adapter selection."""
        console.print("\n[bold]Available Adapters:[/bold]")

        available_adapters = await self.config_manager.get_available_adapters()

        # Group and display adapters
        categories = self._group_adapters_by_category(available_adapters)
        adapter_choices = self._display_adapter_choices(categories)

        # Get user selection
        console.print(
            "\n[bold]Select adapters (comma-separated numbers, e.g., 1,3,5):[/bold]"
        )
        console.print("[dim]Leave empty for recommended defaults[/dim]")
        selection = Prompt.ask("Adapter numbers", default="")

        # Return recommended or parsed selection
        if not selection.strip():
            return self._get_recommended_adapters(available_adapters)

        return self._parse_adapter_selection(selection, adapter_choices)

    def _configure_adapter_env_vars(self, adapter_config: t.Any) -> None:
        """Configure adapter environment variables."""
        if adapter_config.environment_variables:
            console.print("\n[yellow]Environment Variables:[/yellow]")
            for env_var in adapter_config.environment_variables:
                self._configure_environment_variable(env_var)

    def _configure_required_settings(
        self, adapter_config: t.Any, schema: dict[str, t.Any]
    ) -> None:
        """Configure required adapter settings."""
        for setting in schema.get("required_settings", []):
            value = Prompt.ask(
                f"[red]*[/red] {setting['name']} ({setting['type']})",
                default=str(setting.get("default", "")),
            )
            adapter_config.settings[setting["name"]] = self._parse_setting_value(
                value, setting["type"]
            )

    def _configure_optional_settings(
        self, adapter_config: t.Any, schema: dict[str, t.Any]
    ) -> None:
        """Configure optional adapter settings."""
        if schema.get("optional_settings") and Confirm.ask(
            "Configure optional settings?"
        ):
            for setting in schema.get("optional_settings", []):
                if Confirm.ask(f"Configure {setting['name']}?"):
                    value = Prompt.ask(
                        f"{setting['name']} ({setting['type']})",
                        default=str(setting.get("default", "")),
                    )
                    adapter_config.settings[setting["name"]] = (
                        self._parse_setting_value(value, setting["type"])
                    )

    async def _configure_adapter_interactive(
        self, config: ConfigurationSchema, adapter_name: str
    ) -> None:
        """Configure a specific adapter interactively."""
        console.print(f"\n[bold]Configuring {adapter_name} adapter:[/bold]")

        adapter_config = config.adapters[adapter_name]
        schema = await self.config_manager.get_adapter_configuration_schema(
            adapter_name
        )

        # Show adapter information
        console.print(f"[dim]Category: {schema.get('category', 'Unknown')}[/dim]")
        if schema.get("description"):
            console.print(f"[dim]Description: {schema['description']}[/dim]")

        # Configure environment variables
        self._configure_adapter_env_vars(adapter_config)

        # Configure settings
        if schema.get("required_settings") or schema.get("optional_settings"):
            console.print("\n[yellow]Adapter Settings:[/yellow]")
            self._configure_required_settings(adapter_config, schema)
            self._configure_optional_settings(adapter_config, schema)

        # Configure dependencies
        if schema.get("dependencies"):
            console.print(
                f"\n[yellow]Dependencies: {', '.join(schema['dependencies'])}[/yellow]"
            )
            adapter_config.dependencies.update(schema["dependencies"])

    def _configure_environment_variable(self, env_var: EnvironmentVariable) -> None:
        """Configure a single environment variable."""
        current_value = os.environ.get(
            env_var.name, env_var.value or env_var.default or ""
        )

        if env_var.required:
            prompt_text = f"[red]*[/red] {env_var.name}"
        else:
            prompt_text = env_var.name

        if env_var.description:
            console.print(f"[dim]  {env_var.description}[/dim]")

        if env_var.secret:
            value = Prompt.ask(prompt_text, password=True, default=current_value)
        else:
            value = Prompt.ask(prompt_text, default=current_value)

        env_var.value = value

    def _parse_setting_value(self, value: str, type_name: str) -> Any:
        """Parse setting value based on type."""
        if not value:
            return None

        try:
            if type_name in ("int", "integer"):
                return int(value)
            elif type_name in ("float", "number"):
                return float(value)
            elif type_name in ("bool", "boolean"):
                return value.lower() in ("true", "1", "yes", "on")
            elif type_name in ("list", "array"):
                return [item.strip() for item in value.split(",") if item.strip()]
            elif type_name in ("dict", "object"):
                return json.loads(value)

            return value
        except (ValueError, json.JSONDecodeError):
            console.print(
                f"[red]Warning:[/red] Could not parse '{value}' as {type_name}, using as string"
            )
            return value

    async def _configure_global_settings(self, config: ConfigurationSchema) -> None:
        """Configure global settings."""
        console.print("\n[bold]Global Settings:[/bold]")

        if Confirm.ask("Configure global settings?"):
            # Common global settings
            settings_to_configure = [
                ("debug", "bool", "Enable debug mode"),
                ("log_level", "str", "Logging level (DEBUG, INFO, WARNING, ERROR)"),
                ("secret_key", "str", "Application secret key"),
                ("database_url", "str", "Database connection URL"),
            ]

            for setting_name, setting_type, description in settings_to_configure:
                if Confirm.ask(f"Configure {setting_name}?"):
                    console.print(f"[dim]{description}[/dim]")
                    value = Prompt.ask(
                        setting_name,
                        password=(setting_name in ("secret_key", "database_url")),
                    )
                    config.global_settings[setting_name] = self._parse_setting_value(
                        value, setting_type
                    )

    def _display_validation_result(self, result: ConfigurationValidationResult) -> None:
        """Display configuration validation results."""
        if result.status == ConfigurationStatus.VALID:
            console.print("[green]✓ Configuration is valid[/green]")
        elif result.status == ConfigurationStatus.WARNING:
            console.print("[yellow]⚠ Configuration has warnings[/yellow]")
        elif result.status == ConfigurationStatus.ERROR:
            console.print("[red]✗ Configuration has errors[/red]")

        if result.errors:
            console.print("\n[red]Errors:[/red]")
            for error in result.errors:
                console.print(f"  [red]•[/red] {error}")

        if result.warnings:
            console.print("\n[yellow]Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  [yellow]•[/yellow] {warning}")


# CLI Commands


@click.group()
def config_cli() -> None:
    """FastBlocks Configuration Management CLI."""
    pass


@config_cli.command()
def wizard() -> None:
    """Launch the interactive configuration wizard."""

    async def _wizard() -> None:
        cli = InteractiveConfigurationCLI()
        await cli.initialize()
        await cli.run_configuration_wizard()

    asyncio.run(_wizard())


@config_cli.command()
@click.option(
    "--profile",
    type=click.Choice(["development", "staging", "production"]),
    default="development",
    help="Configuration profile",
)
@click.option("--adapters", help="Comma-separated list of adapters to include")
@click.option("--output", "-o", help="Output file path")
def create(profile: str, adapters: str | None, output: str | None) -> None:
    """Create a new configuration file."""

    async def _create() -> None:
        registry = AdapterRegistry()
        config_manager = ConfigurationManager(registry)
        await registry.initialize()
        await config_manager.initialize()

        profile_enum = ConfigurationProfile(profile)
        adapter_list = adapters.split(",") if adapters else None

        config = await config_manager.create_configuration(
            profile=profile_enum, adapters=adapter_list
        )

        config_file = await config_manager.save_configuration(config, output)
        console.print(f"[green]✓[/green] Configuration created: {config_file}")

    asyncio.run(_create())


def _format_json_output(result: ConfigurationValidationResult) -> None:
    """Format validation result as JSON."""
    output = {
        "status": result.status.value,
        "errors": result.errors,
        "warnings": result.warnings,
        "adapter_results": result.adapter_results,
    }
    click.echo(json.dumps(output, indent=2))


def _format_text_output(result: ConfigurationValidationResult) -> None:
    """Format validation result as human-readable text."""
    # Print status
    status_messages = {
        ConfigurationStatus.VALID: "[green]✓ Configuration is valid[/green]",
        ConfigurationStatus.WARNING: "[yellow]⚠ Configuration has warnings[/yellow]",
        ConfigurationStatus.ERROR: "[red]✗ Configuration has errors[/red]",
    }
    console.print(status_messages.get(result.status, "Unknown status"))

    # Print errors
    if result.errors:
        console.print("\n[red]Errors:[/red]")
        for error in result.errors:
            console.print(f"  • {error}")

    # Print warnings
    if result.warnings:
        console.print("\n[yellow]Warnings:[/yellow]")
        for warning in result.warnings:
            console.print(f"  • {warning}")


@config_cli.command()
@click.argument("config_file")
@click.option("--format", type=click.Choice(["text", "json"]), default="text")
def validate(config_file: str, format: str) -> None:
    """Validate a configuration file."""

    async def _validate() -> None:
        registry = AdapterRegistry()
        config_manager = ConfigurationManager(registry)
        await registry.initialize()
        await config_manager.initialize()

        try:
            config = await config_manager.load_configuration(config_file)
            result = await config_manager.validate_configuration(config)

            # Format output based on requested format
            if format == "json":
                _format_json_output(result)
            else:
                _format_text_output(result)

        except FileNotFoundError:
            console.print(
                f"[red]Error:[/red] Configuration file '{config_file}' not found"
            )
            sys.exit(1)
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    asyncio.run(_validate())


@config_cli.command()
@click.argument("config_file")
@click.option("--output", "-o", help="Output .env file path")
def generate_env(config_file: str, output: str | None) -> None:
    """Generate .env file from configuration."""

    async def _generate_env() -> None:
        registry = AdapterRegistry()
        config_manager = ConfigurationManager(registry)
        await registry.initialize()
        await config_manager.initialize()

        try:
            config = await config_manager.load_configuration(config_file)
            output_path = Path(output) if output else None
            env_file = await config_manager.generate_environment_file(
                config, output_path
            )
            console.print(f"[green]✓[/green] Environment file created: {env_file}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    asyncio.run(_generate_env())


@config_cli.command()
def list_templates() -> None:
    """List available configuration templates."""

    async def _list_templates() -> None:
        registry = AdapterRegistry()
        config_manager = ConfigurationManager(registry)
        await config_manager.initialize()

        templates_dir = config_manager.templates_dir
        if not templates_dir.exists():
            console.print("[yellow]No templates directory found[/yellow]")
            return

        templates = list(templates_dir.glob("*.yaml"))
        if not templates:
            console.print("[yellow]No templates available[/yellow]")
            return

        console.print("[bold]Available Templates:[/bold]")
        for template in sorted(templates):
            console.print(f"  • {template.stem}")

    asyncio.run(_list_templates())


@config_cli.command()
@click.argument("name")
@click.argument("description")
def backup(name: str, description: str) -> None:
    """Create a backup of current configuration."""

    async def _backup() -> None:
        # This would need to be implemented based on current active configuration
        console.print(
            "[yellow]Backup functionality needs active configuration context[/yellow]"
        )

    asyncio.run(_backup())


@config_cli.command()
def list_backups() -> None:
    """List all configuration backups."""

    async def _list_backups() -> None:
        registry = AdapterRegistry()
        config_manager = ConfigurationManager(registry)
        await config_manager.initialize()

        backups = await config_manager.list_backups()

        if not backups:
            console.print("[yellow]No backups found[/yellow]")
            return

        ServerPanels.backups_table(backups)

    asyncio.run(_list_backups())


@config_cli.command()
@click.argument("backup_id")
@click.option("--output", "-o", help="Output file path")
def restore(backup_id: str, output: str | None) -> None:
    """Restore configuration from backup."""

    async def _restore() -> None:
        registry = AdapterRegistry()
        config_manager = ConfigurationManager(registry)
        await config_manager.initialize()

        try:
            config = await config_manager.restore_backup(backup_id)

            if output:
                config_file = await config_manager.save_configuration(config, output)
            else:
                config_file = await config_manager.save_configuration(config)

            console.print(f"[green]✓[/green] Configuration restored to: {config_file}")
        except Exception as e:
            console.print(f"[red]Error:[/red] {e}")
            sys.exit(1)

    asyncio.run(_restore())


if __name__ == "__main__":
    config_cli()
