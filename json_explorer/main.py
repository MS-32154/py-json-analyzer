#!/usr/bin/env python3

"""Entry point for the JSON Explorer CLI tool."""

import argparse
import json
import sys
from pathlib import Path
from typing import Any

from rich.console import Console

from .cli import CLIHandler
from .codegen.cli_integration import add_codegen_args, handle_codegen_command
from .errors import JsonExplorerError
from .interactive import InteractiveHandler
from .json_schema import json_schema
from .logging_config import configure_logging, get_logger
from .ui import write_raw
from .utils import load_json

logger = get_logger(__name__)


class JSONExplorer:
    """Main JSON Explorer application coordinator."""

    data: Any
    source: str
    console: Console
    cli_handler: CLIHandler
    interactive_handler: InteractiveHandler

    def __init__(self) -> None:
        """Initialize the JSON Explorer application."""
        self.data = None
        self.source = ""
        self.console = Console()
        self.cli_handler = CLIHandler()
        self.interactive_handler = InteractiveHandler()

    def load_data(self, file_path: str | None = None, url: str | None = None) -> bool:
        """
        Load JSON data from a file or URL.

        Args:
            file_path: Path to a local JSON file.
            url: URL to fetch JSON data from.

        Returns:
            True if data was loaded successfully, False otherwise.
        """
        try:
            self.source, self.data = load_json(file_path, url)
            logger.info("Loaded JSON data from %s", self.source)
            return True
        except (JsonExplorerError, OSError) as e:  # JSONLoaderError, FileNotFoundError
            self.console.print(f"❌ [red]Error loading data: {e}[/red]")
            return False

    def run(self, args: argparse.Namespace) -> int:
        """
        Main execution method.

        Args:
            args: Parsed command-line arguments.

        Returns:
            Exit code: 0 on success, 1 on failure.
        """
        # Handle codegen commands first
        if self._is_codegen_command(args):
            # Informational commands need no input data
            if getattr(args, "list_languages", False) or getattr(
                args, "language_info", None
            ):
                return handle_codegen_command(args, None)
            if not self.load_data(args.file, getattr(args, "url", None)):
                return 1
            return handle_codegen_command(args, self.data)

        # Load data for other operations
        if not self.load_data(args.file, getattr(args, "url", None)):
            return 1

        if getattr(args, "json_schema", False):
            return self._export_json_schema(args)

        self.cli_handler.set_data(self.data, self.source)
        self.interactive_handler.set_data(self.data, self.source)

        if getattr(args, "interactive", False) or not self._has_cli_actions(args):
            return self.interactive_handler.run()
        return self.cli_handler.run(args)

    def _export_json_schema(self, args: argparse.Namespace) -> int:
        """Write the inferred JSON Schema to --output or stdout."""
        title = args.root_name if args.root_name != "Root" else None
        if title is None and args.file:
            title = Path(args.file).stem
        text = json.dumps(json_schema(self.data, title), indent=2, ensure_ascii=False)
        if args.output:
            Path(args.output).write_text(text + "\n", encoding="utf-8")
            Console(stderr=True).print(
                f"[green]✓[/green] JSON Schema saved to {args.output}"
            )
        else:
            write_raw(text)
        return 0

    def _is_codegen_command(self, args: argparse.Namespace) -> bool:
        """Check if the current command is related to code generation."""
        return any(
            getattr(args, attr, False)
            for attr in ["generate", "list_languages", "language_info"]
        )

    def _has_cli_actions(self, args: argparse.Namespace) -> bool:
        """Check if any CLI-specific actions are requested."""
        return any(
            getattr(args, action, False)
            for action in ["tree", "search", "stats", "plot"]
        )


def create_parser() -> argparse.ArgumentParser:
    """
    Create and configure the command-line argument parser.

    Returns:
        Configured argparse.ArgumentParser instance.
    """
    parser = argparse.ArgumentParser(
        description="🔍 JSON Explorer - Analyze, visualize, and explore JSON data",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s data.json --interactive
  %(prog)s data.json --tree compact --stats
  %(prog)s data.json --search "users[*].name"
  %(prog)s data.json --search "users[?age > `30`]"
  %(prog)s --url https://api.example.com/data --plot

JMESPath Query Examples:
  %(prog)s data.json --search "users[0]"                    # First user
  %(prog)s data.json --search "users[*].email"              # All emails
  %(prog)s data.json --search "users[?age > `30`]"          # Filter by age
  %(prog)s data.json --search "sort_by(users, &age)"        # Sort users
  %(prog)s data.json --search "length(users)"               # Count users

Code Generation:
  %(prog)s data.json --generate go --output user.go --root-name User
  %(prog)s data.json --generate python --package-name models
  %(prog)s --list-languages

JSON Schema:
  %(prog)s data.json --json-schema > data.schema.json
        """,
    )

    # Logging arguments
    logging_group = parser.add_argument_group("logging options")
    logging_group.add_argument("--log-file", type=Path, help="Write logs to file")
    logging_group.add_argument(
        "--log-level",
        choices=["DEBUG", "INFO", "WARNING", "ERROR"],
        default="WARNING",
        help="Logging level (default: WARNING; DEBUG shows tracebacks)",
    )

    # Data source
    parser.add_argument("file", nargs="?", help="Path to JSON file")
    parser.add_argument("--url", type=str, help="URL to fetch JSON from")

    # Interactive mode
    parser.add_argument(
        "--interactive", "-i", action="store_true", help="Run in interactive mode"
    )

    # Tree operations
    parser.add_argument(
        "--tree",
        choices=["compact", "analysis", "raw"],
        help="Display JSON tree structure",
    )

    # JMESPath search operations
    search_group = parser.add_argument_group("JMESPath search options")
    search_group.add_argument(
        "--search",
        type=str,
        help="JMESPath query expression (e.g., 'users[*].name' or 'users[?age > `30`]')",
    )
    search_group.add_argument(
        "--tree-results",
        action="store_true",
        help="Display search results in tree format",
    )
    search_group.add_argument(
        "--show-examples",
        action="store_true",
        help="Show JMESPath query examples",
    )

    # Analysis options
    analysis_group = parser.add_argument_group("analysis options")
    analysis_group.add_argument("--stats", action="store_true", help="Show statistics")
    analysis_group.add_argument(
        "--json-schema",
        action="store_true",
        help="Print a JSON Schema (draft 2020-12) of the data, or write it to --output "
        "(runs on its own: other actions are ignored)",
    )
    analysis_group.add_argument(
        "--detailed", action="store_true", help="Show detailed analysis/statistics"
    )

    # Visualization options
    viz_group = parser.add_argument_group("visualization options")
    viz_group.add_argument(
        "--plot", action="store_true", help="Generate visualizations"
    )
    viz_group.add_argument(
        "--plot-format",
        choices=["terminal", "html", "all"],
        default="html",
        help="terminal: text charts; html: report opened in the browser; all: both",
    )
    viz_group.add_argument("--save-path", type=str, help="Path to save visualizations")
    viz_group.add_argument(
        "--no-browser",
        action="store_true",
        help="Don't open browser for HTML visualizations",
    )

    # Codegen arguments
    add_codegen_args(parser)

    return parser


def main() -> int:
    """Main entry point for the JSON Explorer CLI tool."""
    parser = create_parser()
    args = parser.parse_args()

    # Configure logging
    configure_logging(level=args.log_level, log_file=args.log_file)
    logger.info("JSON Explorer starting")

    # If no arguments, show help
    if len(sys.argv) == 1:
        parser.print_help()
        return 1

    # Handle special commands that don't need file/url
    if hasattr(args, "list_languages") and args.list_languages:
        explorer = JSONExplorer()
        return explorer.run(args)

    if hasattr(args, "language_info") and args.language_info:
        explorer = JSONExplorer()
        return explorer.run(args)

    if hasattr(args, "show_examples") and args.show_examples:
        from .search import JsonSearcher

        searcher = JsonSearcher()
        searcher.print_examples()
        return 0

    # Everything below works on loaded data: a file or a URL is required.
    # (--list-languages, --language-info and --show-examples returned above.)
    if not (args.file or args.url):
        what = "Code generation requires" if args.generate else "You must provide"
        print(f"❌ Error: {what} a file path or --url", file=sys.stderr)
        parser.print_help(sys.stderr)
        return 1

    explorer = JSONExplorer()
    return explorer.run(args)


if __name__ == "__main__":
    sys.exit(main())
