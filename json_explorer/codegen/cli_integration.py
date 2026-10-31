"""
CLI integration for code generation functionality.

Provides command-line interface for the codegen module.
"""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rich import box
from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table

from json_explorer.analyzer import analyze_json
from json_explorer.errors import JsonExplorerError
from json_explorer.logging_config import get_logger
from json_explorer.ui import print_metadata, write_raw

from . import (
    GeneratorError,
    generate_from_analysis,
    get_language_info,
    list_all_language_info,
    list_languages,
)
from .core.plugin import LanguagePlugin
from .registry import RegistryError, all_plugins, get_plugin, is_supported

logger = get_logger(__name__)
# Generated code is the program's output and goes to stdout; status messages,
# warnings and metadata go to stderr so `--generate ... > file` stays clean.
console = Console()
err_console = Console(stderr=True)


# ============================================================================
# Exceptions
# ============================================================================


class CLIError(JsonExplorerError):
    """Raised for CLI-related errors."""


# ============================================================================
# Argument Registration
# ============================================================================


def add_codegen_args(parser: argparse.ArgumentParser) -> None:
    """
    Add code generation arguments to existing CLI parser.

    Args:
        parser: ArgumentParser to add arguments to
    """
    # Code generation group
    codegen_group = parser.add_argument_group("code generation")

    codegen_group.add_argument(
        "--generate",
        "-g",
        metavar="LANGUAGE",
        help="Generate code in specified language (use --list-languages to see options)",
    )

    codegen_group.add_argument(
        "--output",
        "-o",
        metavar="FILE",
        help="Output file for generated code or --json-schema (default: stdout)",
    )

    codegen_group.add_argument(
        "--config",
        metavar="FILE",
        help="JSON configuration file for code generation",
    )

    codegen_group.add_argument(
        "--package-name",
        metavar="NAME",
        help="Package/namespace name for generated code",
    )

    codegen_group.add_argument(
        "--root-name",
        metavar="NAME",
        default="Root",
        help="Name for the root data structure (default: Root)",
    )

    codegen_group.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported target languages and exit",
    )

    codegen_group.add_argument(
        "--language-info",
        metavar="LANGUAGE",
        help="Show detailed information about a specific language",
    )

    # Common generation options
    common_group = parser.add_argument_group("common generation options")

    common_group.add_argument(
        "--no-comments",
        action="store_true",
        help="Don't generate comments in output code",
    )

    common_group.add_argument(
        "--verbose",
        action="store_true",
        help="Show generation result metadata",
    )

    # Language-specific flags come from each language plugin
    for plugin in all_plugins():
        plugin.add_cli_arguments(parser)


# ============================================================================
# Command Handlers
# ============================================================================


def handle_codegen_command(
    args: argparse.Namespace,
    json_data: Any = None,
) -> int:
    """
    Handle code generation command from CLI arguments.

    Args:
        args: Parsed command line arguments
        json_data: The loaded JSON document (any JSON value, including null)

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Handle informational commands first
        if hasattr(args, "list_languages") and args.list_languages:
            return _list_languages()

        if hasattr(args, "language_info") and args.language_info:
            return _show_language_info(args.language_info)

        # Check if generation was requested
        if not hasattr(args, "generate") or not args.generate:
            return 0  # No generation requested

        logger.info("Code generation requested: %s", args.generate)

        # Validate language
        language = args.generate.lower()
        if not _validate_language(language):
            return 1

        # Build configuration
        config = _build_config(args, language)

        # Generate code
        return _generate_and_output(json_data, language, config, args)

    except CLIError as e:
        err_console.print(f"[red]✗ Error:[/red] {e}")
        logger.debug("CLI error: %s", e)
        return 1
    except Exception as e:
        err_console.print(f"[red]✗ Unexpected error:[/red] {e}")
        logger.exception("Unexpected error in CLI handler")
        return 1


# ============================================================================
# Informational Commands
# ============================================================================


def _list_languages() -> int:
    """List supported languages with details."""
    try:
        language_info = list_all_language_info()

        if not language_info:
            console.print("[yellow]⚠️ No code generators available[/yellow]")
            return 0

        # Create table
        table = Table(
            title="📋 Supported Languages",
            box=box.ROUNDED,
            title_style="bold cyan",
        )

        table.add_column("Language", style="bold green", no_wrap=True)
        table.add_column("Extension", style="cyan")
        table.add_column("Generator Class", style="dim")
        table.add_column("Aliases", style="gold1")

        for lang_name, info in sorted(language_info.items()):
            aliases = (
                ", ".join(info["aliases"]) if info["aliases"] else "[dim]none[/dim]"
            )

            table.add_row(
                f"🔧 {lang_name}",
                info["file_extension"],
                info["class"],
                aliases,
            )

        console.print()
        console.print(table)
        console.print()

        # Usage hint
        console.print(
            Panel(
                "[bold]Usage:[/bold] json_explorer [dim]input.json[/dim] --generate [cyan]LANGUAGE[/cyan]\n"
                "[bold]Info:[/bold] json_explorer --language-info [cyan]LANGUAGE[/cyan]\n"
                "[bold]Python:[/bold] json_explorer [dim]input.json[/dim] --generate [cyan]python[/cyan] --python-style [yellow]dataclass[/yellow]",
                title="💡 Quick Start",
                border_style="blue",
            )
        )

        logger.info("Listed %s available languages", len(language_info))
        return 0

    except RegistryError as e:
        err_console.print(f"[red]✗ Error listing languages:[/red] {e}")
        logger.debug("Failed to list languages: %s", e)
        return 1


def _show_language_info(language: str) -> int:
    """Show detailed information about a specific language."""
    try:
        if not _validate_language(language, silent=True):
            err_console.print(f"[red]✗ Language '{language}' is not supported[/red]")
            console.print("[dim]Use --list-languages to see available options[/dim]")
            return 1

        info = get_language_info(language)

        # Create info panel
        info_text = f"""[bold]Language:[/bold] {info["name"]}
[bold]File Extension:[/bold] {info["file_extension"]}
[bold]Generator Class:[/bold] {info["class"]}
[bold]Module:[/bold] {info["module"]}"""

        if info["aliases"]:
            info_text += f"\n[bold]Aliases:[/bold] {', '.join(info['aliases'])}"

        console.print()
        console.print(
            Panel(
                info_text,
                title=f"🔧 {info['name'].title()} Generator",
                border_style="green",
            )
        )

        _show_examples(get_plugin(language))

        logger.info("Displayed info for language: %s", language)
        return 0

    except RegistryError as e:
        err_console.print(f"[red]✗ Error getting language info:[/red] {e}")
        logger.debug("Failed to get language info: %s", e)
        return 1


def _show_examples(plugin: LanguagePlugin) -> None:
    """Show the language's CLI examples."""
    if not plugin.examples:
        return
    text = "\n\n".join(
        f"{description}:\n[cyan]json_explorer data.json {arguments}[/cyan]"
        for description, arguments in plugin.examples
    )
    console.print()
    console.print(
        Panel(text, title=f"💡 {plugin.title} Usage Examples", border_style="blue")
    )


# ============================================================================
# Validation & Input
# ============================================================================


def _validate_language(language: str, silent: bool = False) -> bool:
    """Whether a language name or alias is supported (reports it if not)."""
    if is_supported(language):
        return True
    if not silent:
        err_console.print(f"[red]✗ Unsupported language '{language}'[/red]")
        err_console.print(
            f"[dim]Supported languages: {', '.join(list_languages())}[/dim]"
        )
    return False


# ============================================================================
# Configuration Building
# ============================================================================


def _build_config(args: argparse.Namespace, language: str) -> dict:
    """
    Build configuration from CLI arguments.

    Args:
        args: Parsed CLI arguments
        language: Target language

    Returns:
        Configuration dictionary
    """
    config_dict = {}

    # Load from config file if provided
    if hasattr(args, "config") and args.config:
        config_dict.update(_load_config_file(args.config))  # raises CLIError
        logger.info("Loaded config from file: %s", args.config)

    # Override with CLI arguments
    if hasattr(args, "package_name") and args.package_name:
        config_dict["package_name"] = args.package_name

    if hasattr(args, "no_comments") and args.no_comments:
        config_dict["add_comments"] = False

    # Language-specific options
    config_dict.update(get_plugin(language).config_from_args(args))

    logger.debug("Built config with %s options", len(config_dict))
    return config_dict


def _load_config_file(config_path: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with Path(config_path).open(encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise CLIError("Configuration file must contain a JSON object")

        return config
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON in configuration file: {e}") from e
    except OSError as e:
        raise CLIError(f"Failed to read configuration file: {e}") from e


# ============================================================================
# Code Generation & Output
# ============================================================================


def _generate_and_output(
    json_data: dict | list,
    language: str,
    config: dict,
    args: argparse.Namespace,
) -> int:
    """Generate code and handle output with rich formatting."""
    try:
        # Analyze JSON
        logger.info("Analyzing JSON structure...")
        analysis = analyze_json(json_data)

        # Generate code
        root_name = getattr(args, "root_name", "Root")
        logger.info("Generating %s code (root: %s)...", language, root_name)

        result = generate_from_analysis(analysis, language, config, root_name)

        if not result.success:
            err_console.print(
                f"[red]✗ Code generation failed:[/red] {result.error_message}"
            )
            if hasattr(result, "exception") and result.exception:
                err_console.print(f"[dim]Details: {result.exception}[/dim]")
            logger.debug("Generation failed: %s", result.error_message)
            return 1

        # Output code
        output_file = getattr(args, "output", None)
        if output_file:
            _save_to_file(result.code, output_file, language)
        else:
            _display_to_stdout(result.code, language)

        # Show warnings if any
        if result.warnings:
            err_console.print("\n[yellow]⚠️ Warnings:[/yellow]")
            for warning in result.warnings:
                err_console.print(f"  [yellow]•[/yellow] {warning}")

        # Show metadata if verbose
        if hasattr(args, "verbose") and args.verbose and result.metadata:
            print_metadata(err_console, result.metadata, "📊 Generation Metadata")

        logger.info("Code generation completed successfully")
        return 0

    except GeneratorError as e:
        err_console.print(f"[red]✗[/red] {e}")
        logger.debug("Generator error: %s", e)
        return 1
    except Exception as e:
        err_console.print(f"[red]✗ Unexpected failure:[/red] {e}")
        logger.exception("Unexpected failure during generation")
        return 1


def _save_to_file(code: str, output_path: str, language: str) -> None:
    """Save generated code to file."""
    try:
        path = Path(output_path)
        path.write_text(code, encoding="utf-8")
        err_console.print(
            f"[green]✓[/green] Generated {language} code saved to [cyan]{path}[/cyan]"
        )
        logger.info("Code saved to: %s", path)
    except OSError as e:
        err_console.print(f"[red]✗ Failed to write to {output_path}:[/red] {e}")
        logger.debug("Failed to write file: %s", e)
        raise


def _display_to_stdout(code: str, language: str) -> None:
    """Write generated code to stdout.

    On a terminal the code is shown with a header and syntax highlighting.
    When stdout is redirected or piped, the raw code is written unchanged so
    `json_explorer data.json --generate go > models.go` produces a valid file.
    """
    # isatty, not console.is_terminal: Rich treats FORCE_COLOR as a terminal,
    # which would decorate piped output again.
    if not sys.stdout.isatty():
        write_raw(code)
        return

    console.print(f"\n[green]📄 Generated {language.title()} Code\n[/green]")

    # Rich renders unknown languages as plain text
    syntax_lang = language.lower()
    if syntax_lang == "golang":
        syntax_lang = "go"
    elif syntax_lang == "py":
        syntax_lang = "python"

    syntax = Syntax(code, syntax_lang, theme="monokai", padding=1)
    console.print(syntax)
