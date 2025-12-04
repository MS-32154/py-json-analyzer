"""
CLI integration for code generation functionality.

Provides command-line interface for the codegen module.
"""

import argparse
import json
import sys
from pathlib import Path

from rich.console import Console
from rich.panel import Panel
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from . import (
    GeneratorError,
    generate_from_analysis,
    get_language_info,
    list_all_language_info,
    list_supported_languages,
)
from json_explorer.analyzer import analyze_json
from json_explorer.utils import load_json

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)
console = Console()


# ============================================================================
# Exceptions
# ============================================================================


class CLIError(Exception):
    """Raised for CLI-related errors."""

    pass


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
        help="Output file for generated code (default: stdout)",
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

    # Python-specific options
    python_group = parser.add_argument_group("Python-specific options")

    python_group.add_argument(
        "--python-style",
        choices=["dataclass", "pydantic", "typeddict"],
        help="Python code style (default: dataclass)",
    )

    python_group.add_argument(
        "--no-slots",
        action="store_true",
        help="Don't use __slots__ in dataclasses",
    )

    python_group.add_argument(
        "--frozen",
        action="store_true",
        help="Make dataclasses frozen (immutable)",
    )

    python_group.add_argument(
        "--kw-only",
        action="store_true",
        help="Make dataclass fields keyword-only",
    )

    python_group.add_argument(
        "--no-pydantic-field",
        action="store_true",
        help="Don't use Field() in Pydantic models",
    )

    python_group.add_argument(
        "--pydantic-forbid-extra",
        action="store_true",
        help="Forbid extra fields in Pydantic models",
    )

    logger.debug("Code generation arguments added to parser")


# ============================================================================
# Command Handlers
# ============================================================================


def handle_codegen_command(
    args: argparse.Namespace,
    json_data: dict | list | None = None,
) -> int:
    """
    Handle code generation command from CLI arguments.

    Args:
        args: Parsed command line arguments
        json_data: Optional pre-loaded JSON data

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

        logger.info(f"Code generation requested: {args.generate}")

        # Validate language
        language = args.generate.lower()
        if not _validate_language(language):
            return 1

        # Get input data if not provided
        if json_data is None:
            json_data = _get_input_data(args)
            if json_data is None:
                return 1

        # Build configuration
        config = _build_config(args, language)

        # Generate code
        return _generate_and_output(json_data, language, config, args)

    except CLIError as e:
        console.print(f"[red]✗ Error:[/red] {e}")
        logger.error(f"CLI error: {e}")
        return 1
    except Exception as e:
        console.print(f"[red]✗ Unexpected error:[/red] {e}")
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

        logger.info(f"Listed {len(language_info)} available languages")
        return 0

    except Exception as e:
        console.print(f"[red]✗ Error listing languages:[/red] {e}")
        logger.error(f"Failed to list languages: {e}")
        return 1


def _show_language_info(language: str) -> int:
    """Show detailed information about a specific language."""
    try:
        if not _validate_language(language, silent=True):
            console.print(f"[red]✗ Language '{language}' is not supported[/red]")
            console.print("[dim]Use --list-languages to see available options[/dim]")
            return 1

        info = get_language_info(language)

        # Create info panel
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

        # Show language-specific examples
        match language.lower():
            case "python" | "py":
                _show_python_examples()
            case "go" | "golang":
                _show_go_examples()

        logger.info(f"Displayed info for language: {language}")
        return 0

    except Exception as e:
        console.print(f"[red]✗ Error getting language info:[/red] {e}")
        logger.error(f"Failed to get language info: {e}")
        return 1


def _show_python_examples() -> None:
    """Show Python-specific CLI examples."""
    examples_text = """Generate dataclass:
[cyan]json_explorer data.json --generate python --python-style dataclass[/cyan]

Generate Pydantic model:
[cyan]json_explorer data.json --generate python --python-style pydantic[/cyan]

Generate TypedDict:
[cyan]json_explorer data.json --generate python --python-style typeddict[/cyan]

Frozen dataclass with slots:
[cyan]json_explorer data.json --generate python --frozen[/cyan]"""

    console.print()
    console.print(
        Panel(examples_text, title="💡 Python Usage Examples", border_style="blue")
    )


def _show_go_examples() -> None:
    """Show Go-specific CLI examples."""
    examples_text = """Generate basic structure:
[cyan]json_explorer data.json --generate go[/cyan]

Generate to file:
[cyan]json_explorer data.json --generate go --output output.go[/cyan]

Custom package name:
[cyan]json_explorer data.json --generate go --package-name mypackage[/cyan]

No pointers (strict mode):
[cyan]json_explorer data.json --generate go --no-pointers[/cyan]"""

    console.print()
    console.print(
        Panel(examples_text, title="💡 Go Usage Examples", border_style="blue")
    )


# ============================================================================
# Validation & Input
# ============================================================================


def _validate_language(language: str, silent: bool = False) -> bool:
    """Validate that a language is supported."""
    try:
        supported = list_supported_languages()
        if language.lower() not in [lang.lower() for lang in supported]:
            if not silent:
                console.print(f"[red]✗ Unsupported language '{language}'[/red]")
                console.print(f"[dim]Supported languages: {', '.join(supported)}[/dim]")
            return False
        return True
    except Exception:
        if not silent:
            console.print("[red]✗ Failed to validate language[/red]")
        return False


def _get_input_data(args: argparse.Namespace) -> dict | list | None:
    """Get JSON input data from various sources."""
    try:
        if hasattr(args, "file") and args.file:
            _, data = load_json(args.file)
            logger.info(f"Loaded JSON from file: {args.file}")
            return data
        elif hasattr(args, "url") and args.url:
            _, data = load_json(args.url)
            logger.info(f"Loaded JSON from URL: {args.url}")
            return data
        else:
            # Try to read from stdin
            logger.debug("Reading JSON from stdin")
            return json.load(sys.stdin)
    except json.JSONDecodeError as e:
        console.print(f"[red]✗ Invalid JSON input:[/red] {e}")
        logger.error(f"JSON decode error: {e}")
        return None
    except Exception as e:
        console.print(f"[red]✗ Failed to load input:[/red] {e}")
        logger.error(f"Failed to load input: {e}")
        return None


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
        try:
            file_config = _load_config_file(args.config)
            config_dict.update(file_config)
            logger.info(f"Loaded config from file: {args.config}")
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
    match language.lower():
        case "go" | "golang":
            _add_go_config(args, config_dict)
        case "python" | "py":
            _add_python_config(args, config_dict)

    logger.debug(f"Built config with {len(config_dict)} options")
    return config_dict


def _add_go_config(args: argparse.Namespace, config_dict: dict) -> None:
    """Add Go-specific configuration options."""
    if hasattr(args, "no_pointers") and args.no_pointers:
        config_dict["use_pointers_for_optional"] = False

    if hasattr(args, "no_json_tags") and args.no_json_tags:
        config_dict["generate_json_tags"] = False

    if hasattr(args, "no_omitempty") and args.no_omitempty:
        config_dict["json_tag_omitempty"] = False

    if hasattr(args, "json_tag_case") and args.json_tag_case:
        config_dict["json_tag_case"] = args.json_tag_case


def _add_python_config(args: argparse.Namespace, config_dict: dict) -> None:
    """Add Python-specific configuration options."""
    if hasattr(args, "python_style") and args.python_style:
        config_dict["style"] = args.python_style

    if hasattr(args, "no_slots") and args.no_slots:
        config_dict["dataclass_slots"] = False

    if hasattr(args, "frozen") and args.frozen:
        config_dict["dataclass_frozen"] = True

    if hasattr(args, "kw_only") and args.kw_only:
        config_dict["dataclass_kw_only"] = True

    if hasattr(args, "no_pydantic_field") and args.no_pydantic_field:
        config_dict["pydantic_use_field"] = False

    if hasattr(args, "pydantic_forbid_extra") and args.pydantic_forbid_extra:
        config_dict["pydantic_extra_forbid"] = True


def _load_config_file(config_path: str) -> dict:
    """Load configuration from JSON file."""
    try:
        with open(config_path, encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise CLIError("Configuration file must contain a JSON object")

        return config
    except json.JSONDecodeError as e:
        raise CLIError(f"Invalid JSON in configuration file: {e}")
    except OSError as e:
        raise CLIError(f"Failed to read configuration file: {e}")


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
        logger.info(f"Generating {language} code (root: {root_name})...")

        result = generate_from_analysis(analysis, language, config, root_name)

        if not result.success:
            console.print(
                f"[red]✗ Code generation failed:[/red] {result.error_message}"
            )
            if hasattr(result, "exception") and result.exception:
                console.print(f"[dim]Details: {result.exception}[/dim]")
            logger.error(f"Generation failed: {result.error_message}")
            return 1

        # Output code
        output_file = getattr(args, "output", None)
        if output_file:
            _save_to_file(result.code, output_file, language)
        else:
            _display_to_stdout(result.code, language)

        # Show warnings if any
        if result.warnings:
            console.print("\n[yellow]⚠️ Warnings:[/yellow]")
            for warning in result.warnings:
                console.print(f"  [yellow]•[/yellow] {warning}")

        # Show metadata if verbose
        if hasattr(args, "verbose") and args.verbose and result.metadata:
            _display_metadata(result.metadata)

        logger.info("Code generation completed successfully")
        return 0

    except GeneratorError as e:
        console.print(f"[red]✗[/red] {e}")
        logger.error(f"Generator error: {e}")
        return 1
    except Exception as e:
        console.print(f"[red]✗ Unexpected failure:[/red] {e}")
        logger.exception("Unexpected failure during generation")
        return 1


def _save_to_file(code: str, output_path: str, language: str) -> None:
    """Save generated code to file."""
    try:
        path = Path(output_path)
        path.write_text(code, encoding="utf-8")
        console.print(
            f"[green]✓[/green] Generated {language} code saved to [cyan]{path}[/cyan]"
        )
        logger.info(f"Code saved to: {path}")
    except OSError as e:
        console.print(f"[red]✗ Failed to write to {output_path}:[/red] {e}")
        logger.error(f"Failed to write file: {e}")
        raise


def _display_to_stdout(code: str, language: str) -> None:
    """Display generated code to stdout with syntax highlighting."""
    console.print(f"\n[green]📄 Generated {language.title()} Code\n[/green]")

    try:
        # Map language names for syntax highlighting
        syntax_lang = language.lower()
        if syntax_lang == "golang":
            syntax_lang = "go"
        elif syntax_lang == "py":
            syntax_lang = "python"

        syntax = Syntax(code, syntax_lang, theme="monokai", padding=1)
        console.print(syntax)
    except Exception:
        # Fallback to plain text
        console.print(code)


def _display_metadata(metadata: dict) -> None:
    """Display generation metadata in a formatted table."""
    metadata_table = Table(
        title="📊 Generation Metadata",
        box=box.SIMPLE,
        show_header=True,
        header_style="bold cyan",
    )

    metadata_table.add_column("Property", style="bold")
    metadata_table.add_column("Value", style="green")

    for key, value in metadata.items():
        display_key = key.replace("_", " ").title()
        metadata_table.add_row(display_key, str(value))

    console.print()
    console.print(metadata_table)
