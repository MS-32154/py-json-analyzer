from __future__ import annotations
from typing import Any
from rich.console import Console

from .tree_view import print_json_analysis, print_compact_tree
from .search import JsonSearcher
from .stats import DataStatsAnalyzer
from .visualizer import JSONVisualizer
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
        """Handle JMESPath search operations.

        Args:
            args: Parsed CLI arguments containing search parameters.
        """
        query = args.search
        logger.info("Performing JMESPath search: %s", query)

        # Validate query first
        valid, error = self.searcher.validate_query(query)
        if not valid:
            self.console.print(f"❌ [red]Invalid JMESPath query: {error}[/red]")
            logger.error("Invalid JMESPath query: %s", error)
            return

        # Execute search
        result = self.searcher.search(self.data, query)

        # Display results
        if result:
            show_tree = getattr(args, "tree_results", False)
            self.searcher.print_result(result, show_tree=show_tree)
            logger.info("Search completed successfully")
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
        plot_format = getattr(args, "plot_format", "interactive")
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
