from __future__ import annotations
from typing import Any
from rich.console import Console

from .tree_view import print_json_analysis, print_compact_tree
from .search import JsonSearcher, SearchMode
from .stats import DataStatsAnalyzer
from .visualizer import JSONVisualizer
from .filter_parser import FilterExpressionParser
from .logging_config import get_logger

logger = get_logger(__name__)


class CLIHandler:
    """Handle command-line interface (CLI) operations for JSON analysis."""

    def __init__(self) -> None:
        """Initialize CLI handler with default components."""
        self.data: Any | None = None
        self.source: str | None = None
        self.console = Console()
        self.searcher = JsonSearcher()
        self.analyzer = DataStatsAnalyzer()
        self.visualizer = JSONVisualizer()
        logger.debug("CLIHandler initialized")

    def set_data(self, data: Any, source: str) -> None:
        """Set the data and source for processing.

        Args:
            data: The JSON data to process.
            source: The source name or identifier.
        """
        self.data = data
        self.source = source
        logger.info("Data set for source: %s", source)

    def run(self, args: Any) -> int:
        """Run CLI mode operations based on parsed arguments.

        Args:
            args: Parsed CLI arguments (typically from argparse or similar).

        Returns:
            Exit code (0 for success, 1 for failure).
        """
        if not self.data:
            self.console.print("❌ [red]No data loaded[/red]")
            logger.warning("No data loaded; aborting CLI run")
            return 1

        self.console.print(f"📄 Loaded: {self.source}")
        logger.info("Starting CLI operations for source: %s", self.source)

        # Tree operations
        if getattr(args, "tree", None):
            self._handle_tree_display(args.tree)

        # Search operations
        if getattr(args, "search", None):
            self._handle_search(args)

        # Statistics
        if getattr(args, "stats", False):
            self._handle_stats(args)

        # Visualization
        if getattr(args, "plot", False):
            self._handle_visualization(args)

        # Note: Code generation is handled by main.py -> handle_codegen_command()
        # This keeps the CLI focused on core analysis features
        return 0

    def _handle_tree_display(self, tree_type: str) -> None:
        """Handle tree display operations.

        Args:
            tree_type: Type of tree display ('raw', 'analysis', or 'compact').
        """
        self.console.print(f"\n🌳 JSON Tree Structure ({tree_type.title()}):")
        logger.info("Displaying tree: %s", tree_type)

        if tree_type == "raw":
            print_json_analysis(self.data, self.source, show_raw=True)
        elif tree_type == "analysis":
            print_json_analysis(self.data, self.source)
        elif tree_type == "compact":
            print_compact_tree(self.data, self.source)
        else:
            logger.warning("Unknown tree type requested: %s", tree_type)
            self.console.print(f"❌ [red]Unknown tree type: {tree_type}[/red]")

    def _handle_search(self, args: Any) -> None:
        """Handle search operations.

        Args:
            args: Parsed CLI arguments containing search parameters.
        """
        search_mode = SearchMode(args.search_mode)
        search_term = args.search

        logger.info(
            "Performing search: type=%s, term=%s", args.search_type, search_term
        )

        # Determine search type
        results = []
        if args.search_type == "key":
            results = self.searcher.search_keys(self.data, search_term, search_mode)
        elif args.search_type == "value":
            results = self.searcher.search_values(self.data, search_term, search_mode)
        elif args.search_type == "pair":
            if not getattr(args, "search_value", None):
                self.console.print(
                    "❌ [red]--search-value required for pair search[/red]"
                )
                logger.warning("Pair search attempted without search_value")
                return
            results = self.searcher.search_key_value_pairs(
                self.data, search_term, args.search_value, search_mode, search_mode
            )
        elif args.search_type == "filter":
            try:
                filter_func = FilterExpressionParser.parse_filter(search_term)
                results = self.searcher.search_with_filter(self.data, filter_func)
            except Exception as e:
                self.console.print(f"❌ [red]Filter error: {e}[/red]")
                logger.error("Filter search failed: %s", e)
                return
        else:
            self.console.print(f"❌ [red]Unknown search type: {args.search_type}[/red]")
            logger.warning("Unknown search type: %s", args.search_type)
            return

        # Display results
        if results:
            show_tree = getattr(args, "tree_results", False)
            self.searcher.print_results(results, show_tree=show_tree, mode=search_mode)
            self.console.print(f"\n📊 Found {len(results)} result(s)")
            logger.info("Search completed: %d results found", len(results))
        else:
            self.console.print("[yellow]No results found.[/yellow]")
            logger.info("Search completed: no results found")

    def _handle_stats(self, args: Any) -> None:
        """Handle statistics display.

        Args:
            args: Parsed CLI arguments containing stats options.
        """
        self.console.print("\n📊 JSON Statistics:")
        detailed = getattr(args, "detailed", False)
        self.analyzer.print_summary(self.data, detailed=detailed)
        logger.info("Displayed statistics (detailed=%s)", detailed)

    def _handle_visualization(self, args: Any) -> None:
        """Handle visualization generation.

        Args:
            args: Parsed CLI arguments containing visualization options.
        """
        plot_format = getattr(args, "plot_format", "matplotlib")
        save_path = getattr(args, "save_path", None)
        detailed = getattr(args, "detailed", False)
        open_browser = not getattr(args, "no_browser", False)

        try:
            self.visualizer.visualize(
                self.data,
                output=plot_format,
                save_path=save_path,
                detailed=detailed,
                open_browser=open_browser,
            )
            self.console.print(
                "✅ [green]Visualizations generated successfully[/green]"
            )
            logger.info(
                "Visualization generated (format=%s, detailed=%s, path=%s)",
                plot_format,
                detailed,
                save_path,
            )
        except Exception as e:
            self.console.print(f"❌ [red]Visualization error: {e}[/red]")
            logger.error("Visualization error: %s", e)
