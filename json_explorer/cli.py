from rich.console import Console

from .tree_view import print_json_analysis, print_compact_tree
from .search import JsonSearcher, SearchMode
from .stats import DataStatsAnalyzer
from .visualizer import JSONVisualizer
from .filter_parser import FilterExpressionParser
from .analyzer import analyze_json
from .codegen import MultiTargetGenerator, parse_config_string


class CLIHandler:
    """Handle command-line interface operations."""

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

    def run(self, args):
        """Run CLI mode operations based on arguments."""
        if not self.data:
            self.console.print("⌛ [red]No data loaded[/red]")
            return 1

        self.console.print(f"📄 Loaded: {self.source}")

        # Tree operations
        if args.tree:
            self._handle_tree_display(args.tree)

        # Search operations
        if args.search:
            self._handle_search(args)

        # Statistics
        if args.stats:
            self._handle_stats(args)

        # Visualization
        if args.plot:
            self._handle_visualization(args)

        # Code generation
        if args.codegen:
            self._handle_codegen(args)

        return 0

    def _handle_tree_display(self, tree_type):
        """Handle tree display operations."""
        self.console.print(f"\n🌳 JSON Tree Structure ({tree_type.title()}):")

        if tree_type == "raw":
            print_json_analysis(self.data, self.source, show_raw=True)
        elif tree_type == "analysis":
            print_json_analysis(self.data, self.source)
        elif tree_type == "compact":
            print_compact_tree(self.data, self.source)

    def _handle_search(self, args):
        """Handle search operations."""
        search_mode = SearchMode(args.search_mode)
        search_term = args.search

        if args.search_type == "pair":
            self.console.print(
                f"\n🔍 Searching for key-value pair: '{search_term}' = '{args.search_value}'"
            )
        else:
            self.console.print(f"\n🔍 Searching ({args.search_type}): '{search_term}'")

        # Perform search based on type
        if args.search_type == "key":
            results = self.searcher.search_keys(self.data, search_term, search_mode)
        elif args.search_type == "value":
            results = self.searcher.search_values(self.data, search_term, search_mode)
        elif args.search_type == "pair":
            if not args.search_value:
                self.console.print(
                    "⌛ [red]--search-value required for pair search[/red]"
                )
                return
            results = self.searcher.search_key_value_pairs(
                self.data, search_term, args.search_value, search_mode, search_mode
            )
        elif args.search_type == "filter":
            try:
                filter_func = FilterExpressionParser.parse_filter(search_term)
                results = self.searcher.search_with_filter(self.data, filter_func)
            except Exception as e:
                self.console.print(f"⌛ [red]Filter error: {e}[/red]")
                return
        else:
            self.console.print(f"⌛ [red]Unknown search type: {args.search_type}[/red]")
            return

        # Display results
        if results:
            # Check if tree results display is requested
            show_tree = getattr(args, "tree_results", False)
            self.searcher.print_results(results, show_tree=show_tree, mode=search_mode)

            self.console.print(f"\n📊 Found {len(results)} result(s)")
        else:
            self.console.print("[yellow]No results found.[/yellow]")

    def _handle_stats(self, args):
        """Handle statistics display."""
        self.console.print("\n📊 JSON Statistics:")
        detailed = getattr(args, "detailed", False)
        self.analyzer.print_summary(self.data, detailed=detailed)

    def _handle_visualization(self, args):
        """Handle visualization generation."""
        self.console.print("\n📈 Generating visualizations...")

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
        except Exception as e:
            self.console.print(f"⌛ [red]Visualization error: {e}[/red]")

    def _handle_codegen(self, args):
        """Handle code generation."""
        self.console.print("\n🔧 Generating code from JSON schema...")

        try:
            # Analyze JSON to generate schema
            schema = analyze_json(self.data)

            # Create generator
            root_name = getattr(args, "codegen_root", "Root")
            generator = MultiTargetGenerator(schema, root_name=root_name)

            # Parse configuration if provided
            config_dict = {}
            if hasattr(args, "codegen_config") and args.codegen_config:
                config_dict = parse_config_string(args.codegen_config)

            # Handle target selection
            if args.codegen == "all":
                # Generate all targets
                self.console.print("📝 Generating code for all supported targets...")
                results = generator.generate_all(config_dict)

                for target, code in results.items():
                    self.console.print(f"\n{'='*60}")
                    self.console.print(
                        f"🎯 [bold cyan]TARGET: {target.upper()}[/bold cyan]"
                    )
                    self.console.print("=" * 60)
                    print(code)

                self.console.print(
                    f"\n✅ [green]Generated code for {len(results)} targets[/green]"
                )

            elif args.codegen in generator.list_targets():
                # Generate specific target
                self.console.print(f"📝 Generating {args.codegen.upper()} code...")
                code = generator.generate(args.codegen, config_dict)

                self.console.print(
                    f"\n🎯 [bold cyan]{args.codegen.upper()} Code:[/bold cyan]"
                )
                self.console.print("-" * 50)
                print(code)

                self.console.print(f"\n✅ [green]Code generated successfully[/green]")

            else:
                available = ", ".join(generator.list_targets())
                self.console.print(f"⌛ [red]Unknown target: {args.codegen}[/red]")
                self.console.print(
                    f"[yellow]Available targets: {available}, all[/yellow]"
                )

        except Exception as e:
            self.console.print(f"⌛ [red]Code generation error: {e}[/red]")

    def list_codegen_targets(self):
        """List available code generation targets."""
        generator = MultiTargetGenerator({})
        targets = generator.list_targets()

        self.console.print("\n🎯 [bold]Available Code Generation Targets:[/bold]")
        for target in targets:
            self.console.print(f"  • [cyan]{target}[/cyan]")
        self.console.print("  • [cyan]all[/cyan] - Generate code for all targets")
