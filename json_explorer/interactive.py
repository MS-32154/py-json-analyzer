import json
from datetime import datetime

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table

from .tree_view import print_json_analysis, print_compact_tree
from .search import JsonSearcher, SearchMode
from .stats import DataStatsAnalyzer
from .visualizer import JSONVisualizer
from .filter_parser import FilterExpressionParser
from .utils import load_json


class InteractiveHandler:
    """Handle interactive mode operations."""

    def __init__(self):
        self.data = None
        self.source = None
        self.console = Console()
        self.searcher = JsonSearcher()
        self.analyzer = DataStatsAnalyzer()
        self.visualizer = JSONVisualizer()

    def set_data(self, data, source):
        """Set the data and source for processing."""
        self.data = data
        self.source = source

    def run(self):
        """Run interactive mode."""
        if not self.data:
            self.console.print("❌ [red]No data loaded. Please load data first.[/red]")
            return 1

        self.console.print(f"\n🎯 [bold green]Interactive JSON Explorer[/bold green]")
        self.console.print(f"📄 [cyan]Loaded: {self.source}[/cyan]\n")

        while True:
            self._show_main_menu()
            choice = Prompt.ask(
                "\n[bold]Choose an option[/bold]",
                choices=["1", "2", "3", "4", "5", "6", "7", "8", "9", "q"],
                default="q",
            )

            if choice == "q":
                self.console.print("👋 [yellow]Goodbye![/yellow]")
                break
            elif choice == "1":
                self._interactive_tree_view()
            elif choice == "2":
                self._interactive_search()
            elif choice == "3":
                self._interactive_stats()
            elif choice == "4":
                self._interactive_visualization()
            elif choice == "5":
                self._interactive_filter_search()
            elif choice == "6":
                self._interactive_advanced_search()
            elif choice == "7":
                self._show_filter_help()
            elif choice == "8":
                self._load_new_data()
            elif choice == "9":
                self._show_data_summary()

        return 0

    def _show_main_menu(self):
        """Display the main menu."""
        menu_panel = Panel.fit(
            """[bold blue]📋 Main Menu[/bold blue]

[cyan]1.[/cyan] 🌳 Tree View (Structure Analysis)
[cyan]2.[/cyan] 🔍 Search (Keys/Values)
[cyan]3.[/cyan] 📊 Statistics & Analysis
[cyan]4.[/cyan] 📈 Visualizations
[cyan]5.[/cyan] 🎯 Advanced Filter Search
[cyan]6.[/cyan] 🔎 Advanced Search Options
[cyan]7.[/cyan] ❓ Filter Expression Help
[cyan]8.[/cyan] 📁 Load New Data
[cyan]9.[/cyan] 📋 Data Summary
[cyan]q.[/cyan] 🚪 Quit""",
            border_style="blue",
        )
        self.console.print(menu_panel)

    def _interactive_tree_view(self):
        """Interactive tree view options."""
        self.console.print("\n🌳 [bold]Tree View Options[/bold]")

        tree_type = Prompt.ask(
            "Select tree view type",
            choices=["compact", "analysis", "raw"],
            default="compact",
        )

        if tree_type == "raw":
            print_json_analysis(self.data, self.source, show_raw=True)
        elif tree_type == "analysis":
            print_json_analysis(self.data, self.source)
        elif tree_type == "compact":
            print_compact_tree(self.data, self.source)

    def _interactive_search(self):
        """Interactive search functionality."""
        self.console.print("\n🔍 [bold]Search Options[/bold]")

        search_type = Prompt.ask(
            "What would you like to search for?",
            choices=["key", "value", "pair"],
            default="key",
        )

        search_term = Prompt.ask("Enter search term")

        mode_str = Prompt.ask(
            "Search mode",
            choices=[
                "exact",
                "contains",
                "regex",
                "startswith",
                "endswith",
                "case_insensitive",
            ],
            default="exact",
        )
        search_mode = SearchMode(mode_str)

        if search_type == "key":
            self.console.print(f"\n🔍 Searching for key: '{search_term}'")
            results = self.searcher.search_keys(self.data, search_term, search_mode)
            self.searcher.print_results(results, mode=search_mode)

        elif search_type == "value":
            limit_types = Confirm.ask("Limit search to specific data types?")
            value_types = None

            if limit_types:
                type_choices = ["str", "int", "float", "bool", "list", "dict"]
                selected_types = []
                for type_name in type_choices:
                    if Confirm.ask(f"Include {type_name} values?"):
                        selected_types.append(eval(type_name))
                value_types = set(selected_types) if selected_types else None

            self.console.print(f"\n🔍 Searching for value: '{search_term}'")
            results = self.searcher.search_values(
                self.data, search_term, search_mode, value_types=value_types
            )
            self.searcher.print_results(results, mode=search_mode)

        elif search_type == "pair":
            value_term = Prompt.ask("Enter value to search for")
            self.console.print(
                f"\n🔍 Searching for key-value pair: '{search_term}' = '{value_term}'"
            )
            results = self.searcher.search_key_value_pairs(
                self.data, search_term, value_term, search_mode, search_mode
            )
            self.searcher.print_results(results, mode=search_mode)

    def _interactive_stats(self):
        """Interactive statistics display."""
        self.console.print("\n📊 [bold]Statistics & Analysis[/bold]")

        detailed = Confirm.ask("Show detailed statistics?", default=False)
        self.analyzer.print_summary(self.data, detailed=detailed)

    def _interactive_visualization(self):
        """Interactive visualization options."""
        self.console.print("\n📈 [bold]Visualization Options[/bold]")

        viz_format = Prompt.ask(
            "Select visualization format",
            choices=["terminal", "matplotlib", "browser", "all"],
            default="matplotlib",
        )

        detailed = Confirm.ask("Generate detailed visualizations?", default=False)
        save_path = None

        if Confirm.ask("Save visualizations to file?"):
            save_path = Prompt.ask("Enter save path (optional)", default="")
            save_path = save_path if save_path else None

        open_browser = True
        if viz_format in ["browser", "all"]:
            open_browser = Confirm.ask(
                "Open browser for HTML visualizations?", default=True
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
            self.console.print(f"❌ [red]Visualization error: {e}[/red]")

    def _interactive_filter_search(self):
        """Interactive filter search with expression builder."""
        self.console.print("\n🎯 [bold]Advanced Filter Search[/bold]")

        self._show_filter_examples()

        filter_expr = Prompt.ask(
            "\n[bold]Enter filter expression[/bold]",
            default="isinstance(value, (int, float)) and value > 0",
        )

        try:
            filter_func = FilterExpressionParser.parse_filter(filter_expr)

            self.console.print(f"\n🎯 [yellow]Applying filter: {filter_expr}[/yellow]")

            results = self.searcher.search_with_filter(self.data, filter_func)

            if results:
                show_tree = Confirm.ask("Display results as tree?", default=False)
                self.searcher.print_results(results, show_tree=show_tree)

                if Confirm.ask("Save results to file?"):
                    self._save_search_results(results, filter_expr)
            else:
                self.console.print("[yellow]No results found.[/yellow]")

        except Exception as e:
            self.console.print(f"❌ [red]Filter error: {e}[/red]")
            self.console.print(
                "[yellow]Please check your filter expression syntax.[/yellow]"
            )

    def _interactive_advanced_search(self):
        """Advanced search with multiple criteria."""
        self.console.print("\n🔎 [bold]Advanced Search Options[/bold]")

        search_type = Prompt.ask(
            "Select search type",
            choices=["key", "value", "pair", "filter"],
            default="key",
        )

        if search_type == "filter":
            return self._interactive_filter_search()

        search_term = Prompt.ask("Enter search term")
        mode_str = Prompt.ask(
            "Search mode",
            choices=[
                "exact",
                "contains",
                "regex",
                "startswith",
                "endswith",
                "case_insensitive",
            ],
            default="exact",
        )
        search_mode = SearchMode(mode_str)

        self.console.print("\n[bold]Advanced Options:[/bold]")

        max_results = None
        if Confirm.ask("Limit number of results?"):
            max_results = int(Prompt.ask("Maximum results", default="10"))

        min_depth = 0
        max_depth = None
        if Confirm.ask("Set depth limits?"):
            min_depth = int(Prompt.ask("Minimum depth", default="0"))
            if Confirm.ask("Set maximum depth?"):
                max_depth = int(Prompt.ask("Maximum depth", default="5"))

        try:
            if search_type == "key":
                results = self.searcher.search_keys(
                    self.data,
                    search_term,
                    search_mode,
                    max_results=max_results,
                    min_depth=min_depth,
                    max_depth=max_depth,
                )
            elif search_type == "value":
                value_types = (
                    self._get_value_types()
                    if Confirm.ask("Limit to specific data types?")
                    else None
                )
                results = self.searcher.search_values(
                    self.data,
                    search_term,
                    search_mode,
                    value_types=value_types,
                    max_results=max_results,
                    min_depth=min_depth,
                    max_depth=max_depth,
                )
            elif search_type == "pair":
                value_term = Prompt.ask("Enter value to search for")
                results = self.searcher.search_key_value_pairs(
                    self.data, search_term, value_term, search_mode, search_mode
                )

            # Display results
            if results:
                show_tree = Confirm.ask("Display results as tree?", default=False)
                self.searcher.print_results(
                    results, show_tree=show_tree, mode=search_mode
                )
            else:
                self.console.print("[yellow]No results found.[/yellow]")

        except Exception as e:
            self.console.print(f"❌ [red]Search error: {e}[/red]")

    def _get_value_types(self):
        """Get value types selection from user."""
        type_map = {
            "string": str,
            "integer": int,
            "float": float,
            "boolean": bool,
            "list": list,
            "dict": dict,
        }
        selected_types = []
        for type_name, type_class in type_map.items():
            if Confirm.ask(f"Include {type_name}?"):
                selected_types.append(type_class)
        return set(selected_types) if selected_types else None

    def _show_filter_examples(self):
        """Show filter expression examples."""
        examples_panel = Panel.fit(
            """[bold]Example Filter Expressions:[/bold]

[green]• isinstance(value, int) and value > 10[/green]
  Find integer values greater than 10

[green]• key.startswith('user') and depth <= 2[/green]
  Find keys starting with 'user' at depth 2 or less

[green]• 'email' in str(value).lower()[/green]
  Find values containing 'email' (case-insensitive)

[green]• len(str(value)) > 50[/green]
  Find values with string length > 50

[green]• isinstance(value, list) and len(value) > 5[/green]
  Find lists with more than 5 items

[green]• depth == 3 and isinstance(value, dict)[/green]
  Find dictionaries at exactly depth 3""",
            title="💡 Examples",
            border_style="green",
        )
        self.console.print(examples_panel)

    def _show_filter_help(self):
        """Show comprehensive help for filter expressions."""
        help_panel = Panel.fit(
            """[bold blue]🔧 Filter Expression Reference[/bold blue]

[bold]Available Variables:[/bold]
• [cyan]key[/cyan] - The current key name (string)
• [cyan]value[/cyan] - The current value (any type)
• [cyan]depth[/cyan] - Current depth in the JSON structure (integer)

[bold]Available Functions:[/bold]
• [cyan]isinstance(value, type)[/cyan] - Check value type
• [cyan]len(value)[/cyan] - Get length of value
• [cyan]str(value)[/cyan] - Convert to string
• [cyan]int(value)[/cyan], [cyan]float(value)[/cyan] - Type conversion
• [cyan]hasattr(value, attr)[/cyan] - Check if value has attribute
• [cyan]type(value)[/cyan] - Get value type

[bold]String Methods (use with str(value) or key):[/bold]
• [cyan].startswith('prefix')[/cyan]
• [cyan].endswith('suffix')[/cyan]
• [cyan].lower()[/cyan], [cyan].upper()[/cyan]
• [cyan]'substring' in string[/cyan]

[bold]Operators:[/bold]
• Comparison: [cyan]==, !=, <, <=, >, >=[/cyan]
• Logical: [cyan]and, or, not[/cyan]
• Membership: [cyan]in, not in[/cyan]
• Arithmetic: [cyan]+, -, *, /, %[/cyan]

[bold]Complex Examples:[/bold]
[green]isinstance(value, dict) and len(value) > 3[/green]
[green]key.endswith('_id') and isinstance(value, int)[/green]
[green]depth >= 2 and 'user' in key.lower()[/green]
[green]isinstance(value, str) and len(value) > 10 and '@' in value[/green]""",
            border_style="blue",
        )
        self.console.print(help_panel)

    def _load_new_data(self):
        """Load new JSON data."""
        self.console.print("\n📁 [bold]Load New Data[/bold]")

        source_type = Prompt.ask("Data source", choices=["file", "url"], default="file")

        try:
            if source_type == "file":
                file_path = Prompt.ask("Enter file path")
                self.source, self.data = load_json(file_path, None)
            else:
                url = Prompt.ask("Enter URL")
                self.source, self.data = load_json(None, url)

            self.console.print(f"✅ [green]Successfully loaded: {self.source}[/green]")

        except Exception as e:
            self.console.print(f"❌ [red]Failed to load data: {e}[/red]")

    def _show_data_summary(self):
        """Show a quick summary of the loaded data."""
        if not self.data:
            self.console.print("❌ [red]No data loaded[/red]")
            return

        self.console.print("\n📋 [bold]Data Summary[/bold]")

        summary_table = Table(title="Quick Overview")
        summary_table.add_column("Property", style="cyan")
        summary_table.add_column("Value", style="green")

        data_type = type(self.data).__name__
        summary_table.add_row("Data Type", data_type)
        summary_table.add_row("Source", str(self.source))

        if isinstance(self.data, (dict, list)):
            summary_table.add_row("Length", str(len(self.data)))

        if isinstance(self.data, dict):
            summary_table.add_row("Top-level Keys", str(len(self.data.keys())))
            if self.data:
                top_keys = list(self.data.keys())[:5]
                summary_table.add_row(
                    "Sample Keys", ", ".join(str(k) for k in top_keys)
                )

        self.console.print(summary_table)

    def _save_search_results(self, results, filter_expr):
        """Save search results to a file."""
        filename = Prompt.ask(
            "Enter filename",
            default=f"search_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
        )

        try:
            serializable_results = []
            for result in results:
                serializable_results.append(
                    {
                        "path": result.path,
                        "value": result.value,
                        "parent_key": result.parent_key,
                        "depth": result.depth,
                        "data_type": result.data_type,
                    }
                )

            output_data = {
                "filter_expression": filter_expr,
                "timestamp": datetime.now().isoformat(),
                "total_results": len(results),
                "results": serializable_results,
            }

            with open(filename, "w", encoding="utf-8") as f:
                json.dump(output_data, f, indent=2, ensure_ascii=False)

            self.console.print(f"✅ [green]Results saved to: {filename}[/green]")

        except Exception as e:
            self.console.print(f"❌ [red]Error saving results: {e}[/red]")
