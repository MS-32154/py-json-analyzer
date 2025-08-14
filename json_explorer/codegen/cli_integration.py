"""
CLI integration for code generation functionality.

Provides command-line interface for the codegen module.
"""

import argparse
import sys
import json
from pathlib import Path
from typing import Dict, Any, Optional

from . import generate_from_analysis, list_supported_languages, get_generator
from .core.config import ConfigManager, ConfigError
from json_explorer.analyzer import analyze_json
from json_explorer.utils import load_json


def add_codegen_args(parser: argparse.ArgumentParser):
    """Add code generation arguments to CLI parser."""

    # Create codegen subparser
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
        "--list-languages", action="store_true", help="List supported target languages"
    )

    # Language-specific options
    go_group = parser.add_argument_group("Go options")
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


def handle_codegen_command(args: argparse.Namespace) -> int:
    """
    Handle code generation command from CLI arguments.

    Returns:
        Exit code (0 for success, non-zero for error)
    """
    try:
        # Handle list languages
        if args.list_languages:
            return _list_languages()

        # Check if generation was requested
        if not args.generate:
            return 0  # No generation requested

        # Validate language
        language = args.generate.lower()
        supported = list_supported_languages()
        if language not in supported:
            print(f"Error: Unsupported language '{language}'", file=sys.stderr)
            print(f"Supported languages: {', '.join(supported)}", file=sys.stderr)
            return 1

        # Load JSON data
        if hasattr(args, "file") and args.file:
            json_data = load_json(args.file)
        elif hasattr(args, "url") and args.url:
            json_data = load_json(args.url)
        else:
            # Read from stdin
            try:
                json_data = json.load(sys.stdin)
            except json.JSONDecodeError as e:
                print(f"Error: Invalid JSON input: {e}", file=sys.stderr)
                return 1

        # Build configuration
        config = _build_config(args, language)

        # Analyze JSON
        analysis = analyze_json(json_data)

        # Generate code
        result = generate_from_analysis(analysis, language, config, args.root_name)

        if not result.success:
            print(
                f"Error: Code generation failed: {result.error_message}",
                file=sys.stderr,
            )
            return 1

        # Show warnings
        if result.warnings:
            for warning in result.warnings:
                print(f"Warning: {warning}", file=sys.stderr)

        # Output code
        if args.output:
            output_path = Path(args.output)
            try:
                output_path.write_text(result.code, encoding="utf-8")
                print(f"Generated {language} code saved to {output_path}")
            except IOError as e:
                print(f"Error: Failed to write to {output_path}: {e}", file=sys.stderr)
                return 1
        else:
            print(result.code)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1


def _list_languages() -> int:
    """List supported languages."""
    try:
        languages = list_supported_languages()
        if languages:
            print("Supported languages:")
            for lang in languages:
                # Get generator to show additional info
                try:
                    generator = get_generator(lang)
                    ext = generator.file_extension
                    print(f"  {lang:<10} (.{ext.lstrip('.')} files)")
                except Exception:
                    print(f"  {lang}")
        else:
            print("No code generators available")
        return 0
    except Exception as e:
        print(f"Error listing languages: {e}", file=sys.stderr)
        return 1


def _build_config(args: argparse.Namespace, language: str) -> Dict[str, Any]:
    """Build configuration from CLI arguments."""
    config = {}

    # Load from config file if provided
    if hasattr(args, "config") and args.config:
        try:
            config_manager = ConfigManager()
            loaded_config = config_manager._load_config_file(args.config)
            config.update(loaded_config)
        except ConfigError as e:
            raise RuntimeError(f"Configuration error: {e}")

    # Override with CLI arguments
    if hasattr(args, "package_name") and args.package_name:
        config["package_name"] = args.package_name

    # Language-specific options
    if language == "go":
        if hasattr(args, "no_pointers") and args.no_pointers:
            config["use_pointers_for_optional"] = False

        if hasattr(args, "no_json_tags") and args.no_json_tags:
            config["generate_json_tags"] = False

        if hasattr(args, "no_omitempty") and args.no_omitempty:
            config["json_tag_omitempty"] = False

    return config


def create_codegen_subparser(subparsers) -> argparse.ArgumentParser:
    """
    Create a dedicated codegen subcommand parser.

    For use with: json_explorer codegen [options]
    """
    parser = subparsers.add_parser(
        "codegen",
        help="Generate code from JSON schema",
        description="Generate code structures from JSON data analysis",
    )

    # Input options
    input_group = parser.add_mutually_exclusive_group(required=True)
    input_group.add_argument("file", nargs="?", help="JSON file to analyze")
    input_group.add_argument("--url", help="URL to fetch JSON from")
    input_group.add_argument(
        "--stdin", action="store_true", help="Read JSON from standard input"
    )

    # Generation options
    parser.add_argument(
        "--language", "-l", required=True, help="Target language for code generation"
    )

    parser.add_argument("--output", "-o", help="Output file (default: stdout)")

    parser.add_argument("--config", help="Configuration file path")

    parser.add_argument(
        "--root-name", default="Root", help="Name for root structure (default: Root)"
    )

    # Common options
    parser.add_argument("--package-name", "--package", help="Package/namespace name")

    # Go-specific options
    go_group = parser.add_argument_group("Go options")
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

    # List languages
    parser.add_argument(
        "--list-languages",
        action="store_true",
        help="List supported languages and exit",
    )

    parser.set_defaults(func=_handle_codegen_subcommand)

    return parser


def _handle_codegen_subcommand(args: argparse.Namespace) -> int:
    """Handle the codegen subcommand."""
    try:
        if args.list_languages:
            return _list_languages()

        # Get input data
        if args.file:
            json_data = load_json(args.file)
        elif args.url:
            json_data = load_json(args.url)
        elif args.stdin:
            json_data = json.load(sys.stdin)
        else:
            print("Error: No input specified", file=sys.stderr)
            return 1

        # Build config
        config = {}
        if args.config:
            with open(args.config) as f:
                config.update(json.load(f))

        if args.package_name:
            config["package_name"] = args.package_name

        # Go-specific config
        if args.language.lower() == "go":
            if args.no_pointers:
                config["use_pointers_for_optional"] = False
            if args.no_json_tags:
                config["generate_json_tags"] = False
            if args.no_omitempty:
                config["json_tag_omitempty"] = False

        # Analyze and generate
        analysis = analyze_json(json_data)
        result = generate_from_analysis(analysis, args.language, config, args.root_name)

        if not result.success:
            print(f"Error: {result.error_message}", file=sys.stderr)
            return 1

        # Output
        if args.output:
            Path(args.output).write_text(result.code, encoding="utf-8")
            print(f"Code generated: {args.output}")
        else:
            print(result.code)

        # Show warnings
        for warning in result.warnings:
            print(f"Warning: {warning}", file=sys.stderr)

        return 0

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        return 1
