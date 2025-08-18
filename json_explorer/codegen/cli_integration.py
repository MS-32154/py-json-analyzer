"""
CLI integration for code generation functionality.

Provides command-line interface for the codegen module.
"""

import argparse
import sys
import json
from pathlib import Path
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.syntax import Syntax
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich import box

from . import (
    generate_from_analysis,
    list_supported_languages,
    get_generator,
    get_language_info,
    list_all_language_info,
    GeneratorConfig,
    load_config,
    GeneratorError,
)
from json_explorer.analyzer import analyze_json
from json_explorer.utils import load_json


class CLIError(Exception):
    """Exception raised for CLI-related errors."""

    pass


# Initialize rich console
console = Console()


def add_codegen_args(parser: argparse.ArgumentParser):
    """Add code generation arguments to existing CLI parser."""

    # Create codegen subparser group
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
        help="Output file for generated code (default: stdout)",
    )

    codegen_group.add_argument(
        "--config", metavar="FILE", help="JSON configuration file for code generation"
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
        "--struct-case",
        choices=["pascal", "camel", "snake"],
        help="Case style for struct/class names",
    )

    common_group.add_argument(
        "--field-case",
        choices=["pascal", "camel", "snake"],
        help="Case style for field names",
    )

    common_group.add_argument(
        "--verbose",
        action="store_true",
        help="Show generation result metadata",
    )

    # Go-specific options
    go_group = parser.add_argument_group("Go-specific options")
    go_group.add_argument(
        "--no-pointers",
        action="store_true",
        help="Don't use pointers for optional fields in Go",
    )

    go_group.add_argument(
        "--no-json-tags",
        action="store_true",
        help="Don't generate JSON struct tags in Go",
    )

    go_group.add_argument(
        "--no-omitempty",
        action="store_true",
        help="Don't add omitempty to JSON tags in Go",
    )

    go_group.add_argument(
        "--json-tag-case",
        choices=["original", "snake", "camel"],
        help="Case style for JSON tag names in Go",
    )


def handle_codegen_command(args: argparse.Namespace) -> int:
    """
    Handle code generation command from CLI arguments.

    Args:
        args: Parsed command line arguments

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

        # Validate language
        language = args.generate.lower()
        if not _validate_language(language):
            return 1

        # Get input data
        json_data = _get_input_data(args)
        if json_data is None:
            return 1

        # Build configuration
        config = _build_config(args, language)

        # Generate code
        return _generate_and_output(json_data, language, config, args)

    except CLIError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        return 1
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {e}")
        return 1


def create_codegen_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Create a dedicated codegen subcommand parser.

    For use with: json_explorer codegen [options]

    Args:
        subparsers: Subparser group from main parser

    Returns:
        Configured subparser for codegen command
    """
    parser = subparsers.add_parser(
        "codegen",
        help="Generate code from JSON schema",
        description="Generate code structures from JSON data analysis",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  json_explorer codegen --language go --package main data.json
  json_explorer codegen -l python --output models.py --stdin < data.json
  json_explorer codegen --list-languages
  json_explorer codegen --language-info go
        """.strip(),
    )

    # Input options (mutually exclusive)
    input_group = parser.add_mutually_exclusive_group(required=False)
    input_group.add_argument("file", nargs="?", help="JSON file to analyze")
    input_group.add_argument("--url", help="URL to fetch JSON from")
    input_group.add_argument(
        "--stdin", action="store_true", help="Read JSON from standard input"
    )

    # Core generation options
    parser.add_argument("--language", "-l", help="Target language for code generation")

    parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    parser.add_argument("--config", help="Configuration file path (JSON)")

    parser.add_argument(
        "--root-name", default="Root", help="Name for root structure (default: Root)"
    )

    # Common options
    parser.add_argument("--package-name", "--package", help="Package/namespace name")

    parser.add_argument(
        "--no-comments",
        action="store_true",
        help="Don't add comments to generated code",
    )

    parser.add_argument(
        "--struct-case",
        choices=["pascal", "camel", "snake"],
        help="Naming case for structs/classes",
    )

    parser.add_argument(
        "--field-case",
        choices=["pascal", "camel", "snake"],
        help="Naming case for fields",
    )

    # Go-specific options
    go_group = parser.add_argument_group("Go-specific options")
    go_group.add_argument(
        "--no-pointers",
        action="store_true",
        help="Don't use pointers for optional fields",
    )
    go_group.add_argument(
        "--no-json-tags", action="store_true", help="Don't generate JSON struct tags"
    )
    go_group.add_argument(
        "--no-omitempty", action="store_true", help="Don't add omitempty to JSON tags"
    )
    go_group.add_argument(
        "--json-tag-case",
        choices=["original", "snake", "camel"],
        help="Case style for JSON tag names",
    )

    # Informational commands
    info_group = parser.add_argument_group("information")
    info_group.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported languages and exit",
    )
    info_group.add_argument(
        "--language-info",
        metavar="LANGUAGE",
        help="Show detailed info about a language and exit",
    )

    parser.set_defaults(func=_handle_codegen_subcommand)
    return parser


def _handle_codegen_subcommand(args: argparse.Namespace) -> int:
    """Handle the codegen subcommand."""
    try:
        # Handle info commands
        if args.list_languages:
            return _list_languages()

        if args.language_info:
            return _show_language_info(args.language_info)

        # Require language for generation
        if not args.language:
            console.print("[red]✗[/red] --language is required for code generation")
            return 1

        # Require input
        if not (args.file or args.url or args.stdin):
            console.print(
                "[red]✗[/red] Input source required (file, --url, or --stdin)"
            )
            return 1

        # Get input data
        json_data = _get_subcommand_input(args)
        if json_data is None:
            return 1

        # Validate language
        if not _validate_language(args.language):
            return 1

        # Build config
        config = _build_subcommand_config(args)

        # Generate and output
        return _generate_and_output(json_data, args.language, config, args)

    except Exception as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        return 1


def _list_languages() -> int:
    """List supported languages with details."""
    try:
        language_info = list_all_language_info()

        if not language_info:
            console.print("[yellow]⚠️ No code generators available[/yellow]")
            return 0

        # Create a rich table
        table = Table(
            title="📋 Supported Languages", box=box.ROUNDED, title_style="bold cyan"
        )

        table.add_column("Language", style="bold green", no_wrap=True)
        table.add_column("Extension", style="cyan")
        table.add_column("Generator Class", style="dim")
        table.add_column("Aliases", style="blue")

        for lang_name, info in sorted(language_info.items()):
            aliases = (
                ", ".join(info["aliases"]) if info["aliases"] else "[dim]none[/dim]"
            )

            table.add_row(
                f"🔧 {lang_name}", info["file_extension"], info["class"], aliases
            )

        console.print()
        console.print(table)
        console.print()

        # Add usage hint
        console.print(
            Panel(
                "[bold]Usage:[/bold] json_explorer [dim]input.json[/dim] --generate [cyan]LANGUAGE[/cyan]\n"
                "[bold]Info:[/bold] json_explorer codegen --language-info [cyan]LANGUAGE[/cyan]",
                title="💡 Quick Start",
                border_style="blue",
            )
        )

        return 0

    except Exception as e:
        console.print(f"[red]✗ Error listing languages:[/red] {e}")
        return 1


def _show_language_info(language: str) -> int:
    """Show detailed information about a specific language."""
    try:
        if not _validate_language(language, silent=True):
            console.print(f"[red]✗ Language '{language}' is not supported[/red]")
            console.print("[dim]Use --list-languages to see available options[/dim]")
            return 1

        info = get_language_info(language)

        # Create main info panel
        info_text = f"""[bold]Language:[/bold] {info['name']}
[bold]File Extension:[/bold] {info['file_extension']}
[bold]Generator Class:[/bold] {info['class']}
[bold]Module:[/bold] {info['module']}"""

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

        # Try to get configuration details
        try:
            generator = get_generator(language)

            # Create configuration table
            config_table = Table(
                title="⚙️  Default Configuration",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold cyan",
            )

            config_table.add_column("Setting", style="bold")
            config_table.add_column("Value", style="green")

            config_table.add_row("Package Name", str(generator.config.package_name))
            config_table.add_row("Indent Size", str(generator.config.indent_size))
            config_table.add_row(
                "Generate JSON Tags", str(generator.config.generate_json_tags)
            )
            config_table.add_row("Add Comments", str(generator.config.add_comments))
            config_table.add_row(
                "JSON Tag Omitempty", str(generator.config.json_tag_omitempty)
            )

            console.print()
            console.print(config_table)

        except Exception:
            console.print(
                "\n[yellow]⚠️  Could not retrieve configuration details[/yellow]"
            )

        # Add examples panel
        examples_text = f"""Generate basic structure:
[cyan]json_explorer codegen --language {language} data.json[/cyan]

Generate to file:
[cyan]json_explorer codegen -l {language} -o output{info['file_extension']} data.json[/cyan]

Custom package name:
[cyan]json_explorer codegen -l {language} --package mypackage data.json[/cyan]"""

        console.print()
        console.print(
            Panel(examples_text, title="💡 Usage Examples", border_style="blue")
        )

        return 0

    except Exception as e:
        console.print(f"[red]✗ Error getting language info:[/red] {e}")
        return 1


def _validate_language(language: str, silent: bool = False) -> bool:
    """Validate that a language is supported."""
    supported = list_supported_languages()
    if language.lower() not in [lang.lower() for lang in supported]:
        if not silent:
            console.print(f"[red]✗ Unsupported language '{language}'[/red]")
            console.print(f"[dim]Supported languages: {', '.join(supported)}[/dim]")
        return False
    return True


def _get_input_data(args: argparse.Namespace):
    """Get JSON input data from various sources."""
    try:
        if hasattr(args, "file") and args.file:
            return load_json(args.file)[1]
        elif hasattr(args, "url") and args.url:
            return load_json(args.url)[1]
        else:
            # Try to read from stdin
            return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON input:[/red] {e}")
        return None
    except Exception as e:
        console.print(f"[red]✗ Failed to load input:[/red] {e}")
        return None


def _get_subcommand_input(args: argparse.Namespace):
    """Get input data for subcommand."""
    try:
        if args.file:
            return load_json(args.file)[1]
        elif args.url:
            return load_json(args.url)[1]
        elif args.stdin:
            return json.load(sys.stdin)
        else:
            raise CLIError("No input source specified")
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON input: {e}")
    except Exception as e:
        raise CLIError(f"Failed to load input: {e}")


def _build_config(args: argparse.Namespace, language: str) -> GeneratorConfig:
    """Build configuration from CLI arguments."""
    config_dict = {}

    # Load from config file if provided
    if hasattr(args, "config") and args.config:
        try:
            base_config = load_config(config_file=args.config)
            # Convert to dict to merge with CLI options
            config_dict.update(
                {
                    "package_name": base_config.package_name,
                    "indent_size": base_config.indent_size,
                    "use_tabs": base_config.use_tabs,
                    "struct_case": base_config.struct_case,
                    "field_case": base_config.field_case,
                    "generate_json_tags": base_config.generate_json_tags,
                    "json_tag_omitempty": base_config.json_tag_omitempty,
                    "json_tag_case": base_config.json_tag_case,
                    "add_comments": base_config.add_comments,
                    **base_config.language_config,
                }
            )
        except Exception as e:
            raise CLIError(f"Configuration error: {e}")

    # Override with CLI arguments
    if hasattr(args, "package_name") and args.package_name:
        config_dict["package_name"] = args.package_name

    if hasattr(args, "no_comments") and args.no_comments:
        config_dict["add_comments"] = False

    if hasattr(args, "struct_case") and args.struct_case:
        config_dict["struct_case"] = args.struct_case

    if hasattr(args, "field_case") and args.field_case:
        config_dict["field_case"] = args.field_case

    # Language-specific options
    if language.lower() == "go":
        if hasattr(args, "no_pointers") and args.no_pointers:
            config_dict["use_pointers_for_optional"] = False

        if hasattr(args, "no_json_tags") and args.no_json_tags:
            config_dict["generate_json_tags"] = False

        if hasattr(args, "no_omitempty") and args.no_omitempty:
            config_dict["json_tag_omitempty"] = False

        if hasattr(args, "json_tag_case") and args.json_tag_case:
            config_dict["json_tag_case"] = args.json_tag_case

    return load_config(custom_config=config_dict)


def _build_subcommand_config(args: argparse.Namespace) -> GeneratorConfig:
    """Build configuration for subcommand."""
    config_dict = {}

    # Load from config file if provided
    if args.config:
        try:
            with open(args.config, "r", encoding="utf-8") as f:
                file_config = json.load(f)
            config_dict.update(file_config)
        except Exception as e:
            raise CLIError(f"Failed to load config file: {e}")

    # Override with CLI arguments
    if args.package_name:
        config_dict["package_name"] = args.package_name

    if args.no_comments:
        config_dict["add_comments"] = False

    if args.struct_case:
        config_dict["struct_case"] = args.struct_case

    if args.field_case:
        config_dict["field_case"] = args.field_case

    # Go-specific config
    if args.language.lower() == "go":
        if args.no_pointers:
            config_dict["use_pointers_for_optional"] = False
        if args.no_json_tags:
            config_dict["generate_json_tags"] = False
        if args.no_omitempty:
            config_dict["json_tag_omitempty"] = False
        if args.json_tag_case:
            config_dict["json_tag_case"] = args.json_tag_case

    return load_config(custom_config=config_dict)


def _generate_and_output(
    json_data, language: str, config: GeneratorConfig, args: argparse.Namespace
) -> int:
    """Generate code and handle output with rich formatting."""
    try:
        # Show analysis progress
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:

            # Analyze JSON
            analyze_task = progress.add_task(
                "[cyan]Analyzing JSON structure...", total=None
            )
            analysis = analyze_json(json_data)
            progress.remove_task(analyze_task)

            # Generate code
            gen_task = progress.add_task(
                f"[green]Generating {language} code...", total=None
            )
            root_name = getattr(args, "root_name", "Root")
            result = generate_from_analysis(analysis, language, config, root_name)
            progress.remove_task(gen_task)

        if not result.success:
            console.print(
                f"[red]✗ Code generation failed:[/red] {result.error_message}"
            )
            if hasattr(result, "exception") and result.exception:
                console.print(f"[dim]Details: {result.exception}[/dim]")
            return 1

        # Output code
        output_file = getattr(args, "output", None)
        if output_file:
            try:
                output_path = Path(output_file)
                output_path.write_text(result.code, encoding="utf-8")
                console.print(
                    f"[green]✓[/green] Generated {language} code saved to [cyan]{output_path}[/cyan]"
                )
            except IOError as e:
                console.print(f"[red]✗ Failed to write to {output_path}:[/red] {e}")
                return 1
        else:
            top_border = "═" * 40
            console.print(
                f"[green]{top_border} 📄 Generated {language.title()} Code {top_border}[/green]\n"
            )
            # Display code with syntax highlighting
            try:
                syntax = Syntax(result.code, language, theme="monokai")
                console.print(syntax)

            except Exception:
                # Fallback to plain text if syntax highlighting fails
                console.print(result.code)
            console.print(f"\n[green]{top_border}{top_border}{top_border}[/green]")

        # Show metadata if verbose
        if hasattr(args, "verbose") and args.verbose and result.metadata:
            metadata_table = Table(
                title="📊 Generation Metadata",
                box=box.SIMPLE,
                show_header=True,
                header_style="bold cyan",
            )

            metadata_table.add_column("Property", style="bold")
            metadata_table.add_column("Value", style="green")

            for key, value in result.metadata.items():
                metadata_table.add_row(key.replace("_", " ").title(), str(value))

            console.print()
            console.print(metadata_table)

        # Show warnings with rich formatting
        if result.warnings:
            console.print("\n[yellow]⚠️  Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  [yellow]•[/yellow] {warning}")
            console.print()

        return 0

    except GeneratorError as e:
        console.print(f"[red]✗[/red] {e}")
        return 1
    except Exception as e:
        console.print(f"[red]✗ Unexpected failure:[/red] {e}")
        return 1


# Utility functions for testing and development
def validate_cli_config(args: argparse.Namespace) -> bool:
    """
    Validate CLI configuration for development/testing.

    Args:
        args: Parsed CLI arguments

    Returns:
        True if configuration is valid
    """
    try:
        if hasattr(args, "generate") and args.generate:
            # Check language support
            if not _validate_language(args.generate, silent=True):
                return False

            # Try to build config
            config = _build_config(args, args.generate)

            # Try to create generator
            generator = get_generator(args.generate, config)

            return True
    except Exception:
        return False

    return True
