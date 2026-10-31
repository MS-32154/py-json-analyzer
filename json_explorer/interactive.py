from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path
from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt

from .codegen.interactive import CodegenInteractiveHandler
from .logging_config import get_logger
from .search import JsonSearcher
from .stats import DataStatsAnalyzer
from .tree_view import print_compact_tree, print_json_analysis
from .utils import load_json, prompt_input, prompt_input_path
from .visualizer import JSONVisualizer

logger = get_logger(__name__)


class InteractiveHandler:
    """Handle interactive mode operations for JSON analysis."""

    def __init__(self) -> None:
        """Initialize interactive handler with default components."""
        self.data: Any | None = None
        self.source: str | None = None
        self.console = Console()
        self.searcher = JsonSearcher()
        self.analyzer = DataStatsAnalyzer()
        self.visualizer = JSONVisualizer()
        logger.debug("InteractiveHandler initialized")

    def set_data(self, data: Any, source: str) -> None:
        """Set the JSON data and its source for interactive processing.

        Args:
            data: The JSON data to process.
            source: Source name or identifier.
        """
        self.data = data
        self.source = source
        logger.info("Data set for interactive mode: %s", source)

    def run(self) -> int:
        """Run the interactive JSON explorer loop.

        Returns:
            Exit code (0 for success, 1 if no data loaded).
        """
        if self.data is None:
            self.console.print("⚠️ [red]No data loaded. Please load data first.[/red]")
            return 1

        self.console.print("\n🎯 [bold green]Interactive JSON Explorer[/bold green]")
        self.console.print(f"📄 [cyan]Loaded: {self.source}[/cyan]\n")

        actions = {
            "1": self._interactive_tree_view,
            "2": self._interactive_jmespath_search,
            "3": self._interactive_stats,
            "4": self._interactive_visualization,
            "5": self._interactive_codegen,
            "6": self._load_new_data,
        }
        while True:
            self._show_main_menu()
            choice = Prompt.ask(
                "\n[bold]Choose an option[/bold]",
                choices=[*actions, "q"],
                default="q",
            )
            if choice == "q":
                self.console.print("👋 [yellow]Goodbye![/yellow]")
                break
            actions[choice]()

        return 0

    def _input(self, message: str, default: str | None = None, **kwargs) -> str:
        return prompt_input(
            message,
            default=default,
            choices=kwargs.get("choices"),
            console=self.console,
        )

    def _input_path(self, message: str, default: str = "") -> str:
        return prompt_input_path(message, default=default)

    def _show_main_menu(self) -> None:
        """Display the main menu."""
        menu_panel = Panel.fit(
            """[bold blue]📋 Main Menu[/bold blue]

[cyan]1.[/cyan] 🌳 Tree View (Structure Analysis)
[cyan]2.[/cyan] 🔍 JMESPath Search
[cyan]3.[/cyan] 📊 Statistics & Analysis
[cyan]4.[/cyan] 📈 Visualizations
[cyan]5.[/cyan] ⚡ Code Generation
[cyan]6.[/cyan] 📂 Load New Data
[cyan]q.[/cyan] 🚪 Quit""",
            border_style="blue",
        )
        self.console.print(menu_panel)

    def _interactive_tree_view(self) -> None:
        """Interactive tree view options."""
        self.console.print("\n🌳 [bold]Tree View Options[/bold]")
        tree_type = self._input(
            "Select tree view type",
            choices=["compact", "analysis", "raw"],
            default="compact",
        )
        logger.info("User selected tree view type: %s", tree_type)

        if tree_type == "raw":
            print_json_analysis(self.data, self.source, show_raw=True)
        elif tree_type == "analysis":
            print_json_analysis(self.data, self.source)
        elif tree_type == "compact":
            print_compact_tree(self.data, self.source)

    def _interactive_jmespath_search(self) -> None:
        """Interactive JMESPath search functionality."""
        self.console.print("\n🔍 [bold]JMESPath Search[/bold]")
        self.console.print("[dim]Enter a JMESPath query to search your data[/dim]\n")

        # Show examples first if user wants
        if Confirm.ask("Show example queries?", default=True):
            self.searcher.print_examples()

        # Get query from user
        query = self._input(
            "\n[bold]Enter JMESPath query[/bold]",
            default="@",  # @ returns entire document
        )

        logger.info("Interactive JMESPath search: %s", query)

        # Validate query
        valid, error = self.searcher.validate_query(query)
        if not valid:
            self.console.print(f"❌ [red]Invalid query: {error}[/red]")
            return

        # Execute search
        result = self.searcher.search(self.data, query)

        # Display results
        if result:
            show_tree = Confirm.ask("Display results as tree?", default=False)
            self.searcher.print_result(result, show_tree=show_tree)

            if Confirm.ask("\nSave results to file?"):
                self._save_search_result(result)
        else:
            self.console.print("[yellow]No results found.[/yellow]")

    def _interactive_stats(self) -> None:
        """Interactive statistics display."""
        self.console.print("\n📊 [bold]Statistics & Analysis[/bold]")
        detailed = Confirm.ask("Show detailed statistics?", default=False)
        logger.info("Displaying statistics (detailed=%s)", detailed)
        self.analyzer.print_summary(self.data, detailed=detailed)

    def _interactive_visualization(self) -> None:
        """Interactive visualization options."""
        self.console.print("\n📈 [bold]Visualization Options[/bold]")
        viz_format = self._input(
            "Select visualization format",
            choices=["terminal", "html", "all"],
            default="html",
        )
        detailed = Confirm.ask("Generate detailed visualizations?", default=False)
        save_path = None

        open_browser = False

        if viz_format in ["html", "all"]:
            if Confirm.ask("Save visualizations to file?"):
                save_path = self._input("Enter save path (optional)", default="")
                save_path = save_path if save_path else None

            open_browser = Confirm.ask(
                "Open browser for HTML visualizations?", default=True
            )

        logger.info(
            "Visualization requested: format=%s, detailed=%s, save_path=%s",
            viz_format,
            detailed,
            save_path,
        )

        try:
            self.visualizer.visualize(
                self.data,
                output=viz_format,
                save_path=save_path,
                detailed=detailed,
                open_browser=open_browser,
            )
        except Exception as e:
            self.console.print(f"⚠️ [red]Visualization error: {e}[/red]")

    def _interactive_codegen(self) -> None:
        """Interactive code generation functionality."""
        codegen_handler = CodegenInteractiveHandler(self.data, self.console)
        codegen_handler.run_interactive()
        logger.info("Interactive code generation completed")

    def _load_new_data(self) -> None:
        """Load new JSON data from file or URL."""
        self.console.print("\n📂 [bold]Load New Data[/bold]")
        source_type = self._input(
            "Data source", choices=["file", "url"], default="file"
        )

        try:
            if source_type == "file":
                file_path = self._input_path("Enter file path")
                self.source, self.data = load_json(file_path, None)
            else:
                url = self._input("Enter URL")
                self.source, self.data = load_json(None, url)

            self.console.print(f"✅ [green]Successfully loaded: {self.source}[/green]")
        except Exception as e:
            self.console.print(f"⚠️ [red]Failed to load data: {e}[/red]")

    def _save_search_result(self, result: Any) -> None:
        """Save a single search result to a JSON file.

        Args:
            result: SearchResult object to save.
        """
        filename = self._input(
            "Enter filename",
            default=f"search_result_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )
        try:
            output_data = {
                "query": result.query,
                "timestamp": datetime.now().isoformat(),
                "result_type": result.data_type,
                "result": result.value,
            }
            with Path(filename).open("w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)
            self.console.print(f"✅ [green]Result saved to: {filename}[/green]")
        except Exception as e:
            self.console.print(f"⚠️ [red]Error saving result: {e}[/red]")
