"""
CLI integration for code generation functionality.

Provides command-line interface for the codegen module.
"""

import argparse
import sys
import json
from pathlib import Path
from rich.console import Console

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
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Unexpected error: {e}", file=sys.stderr)
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
            print("Error: --language is required for code generation", file=sys.stderr)
            return 1

        # Require input
        if not (args.file or args.url or args.stdin):
            print(
                "Error: Input source required (file, --url, or --stdin)",
                file=sys.stderr,
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
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _list_languages() -> int:
    """List supported languages with details."""
    try:
        language_info = list_all_language_info()

        if not language_info:
            print("No code generators available")
            return 0

        print("Supported languages:")
        print()

        for lang_name, info in sorted(language_info.items()):
            print(f"  {lang_name}")
            print(f"    Extension: {info['file_extension']}")
            print(f"    Class: {info['class']}")
            if info["aliases"]:
                print(f"    Aliases: {', '.join(info['aliases'])}")
            print()

        return 0

    except Exception as e:
        print(f"Error listing languages: {e}", file=sys.stderr)
        return 1


def _show_language_info(language: str) -> int:
    """Show detailed information about a specific language."""
    try:
        if not _validate_language(language, silent=True):
            print(f"Error: Language '{language}' is not supported", file=sys.stderr)
            print("Use --list-languages to see available options", file=sys.stderr)
            return 1

        info = get_language_info(language)

        print(f"Language: {info['name']}")
        print(f"File extension: {info['file_extension']}")
        print(f"Generator class: {info['class']}")
        print(f"Module: {info['module']}")

        if info["aliases"]:
            print(f"Aliases: {', '.join(info['aliases'])}")

        # Try to get a sample generator to show default config
        try:
            generator = get_generator(language)
            print(f"\nDefault configuration:")
            print(f"  Package name: {generator.config.package_name}")
            print(f"  Indent size: {generator.config.indent_size}")
            print(f"  Generate JSON tags: {generator.config.generate_json_tags}")
            print(f"  Add comments: {generator.config.add_comments}")
        except Exception:
            pass

        return 0

    except Exception as e:
        print(f"Error getting language info: {e}", file=sys.stderr)
        return 1


def _validate_language(language: str, silent: bool = False) -> bool:
    """Validate that a language is supported."""
    supported = list_supported_languages()
    if language.lower() not in [lang.lower() for lang in supported]:
        if not silent:
            print(f"Error: Unsupported language '{language}'", file=sys.stderr)
            print(f"Supported languages: {', '.join(supported)}", file=sys.stderr)
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
        print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
        return None
    except Exception as e:
        print(f"Error: Failed to load input: {e}", file=sys.stderr)
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
    """Generate code and handle output."""
    try:
        # Analyze JSON
        analysis = analyze_json(json_data)

        # Generate code
        root_name = getattr(args, "root_name", "Root")
        result = generate_from_analysis(analysis, language, config, root_name)

        if not result.success:
            print(
                f"Error: Code generation failed: {result.error_message}",
                file=sys.stderr,
            )
            if hasattr(result, "exception") and result.exception:
                print(f"Details: {result.exception}", file=sys.stderr)
            return 1

        # Show warnings
        if result.warnings:
            for warning in result.warnings:
                print(f"Warning: {warning}", file=sys.stderr)

        # Output code
        output_file = getattr(args, "output", None)
        if output_file:
            try:
                output_path = Path(output_file)
                output_path.write_text(result.code, encoding="utf-8")
                print(f"Generated {language} code saved to {output_path}")
            except IOError as e:
                print(f"Error: Failed to write to {output_path}: {e}", file=sys.stderr)
                return 1
        else:
            print(result.code)

        # Show metadata if verbose
        if hasattr(args, "verbose") and args.verbose and result.metadata:
            print(f"\nGeneration metadata:", file=sys.stderr)
            for key, value in result.metadata.items():
                print(f"  {key}: {value}", file=sys.stderr)

        return 0

    except GeneratorError as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
    except Exception as e:
        print(f"Error: Unexpected failure: {e}", file=sys.stderr)
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
