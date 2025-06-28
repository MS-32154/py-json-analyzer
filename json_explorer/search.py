from typing import Any, List, Optional
from dataclasses import dataclass
from enum import Enum
import re
from rich.console import Console
from rich.table import Table
from rich.tree import Tree
from rich import print as rprint


class SearchMode(Enum):
    """Search mode options."""

    EXACT = "exact"
    CONTAINS = "contains"
    REGEX = "regex"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    CASE_INSENSITIVE = "case_insensitive"

    def __str__(self):
        return self.value

    @classmethod
    def _missing_(cls, value):
        for member in cls:
            if member.value == value:
                return member
        return None


@dataclass
class SearchResult:
    """Represents a search result with path and context."""

    path: str
    value: Any
    parent_key: Optional[str] = None
    parent_value: Optional[Any] = None
    depth: int = 0
    data_type: str = ""

    def __post_init__(self):
        self.data_type = type(self.value).__name__


class JsonSearcher:
    """Enhanced JSON search utility with multiple search modes and rich output."""

    def __init__(self, console: Optional[Console] = None):
        self.console = console or Console()
        self.results: List[SearchResult] = []

    def search_keys(
        self,
        data,
        target_key,
        mode: SearchMode = SearchMode.EXACT,
        max_results=None,
        min_depth=0,
        max_depth=None,
    ) -> List[SearchResult]:
        """Search for keys in JSON data with various matching modes."""
        self.results = []
        self._search_keys_recursive(
            data, target_key, mode, "root", 0, min_depth, max_depth
        )

        if max_results:
            self.results = self.results[:max_results]

        return self.results

    def search_values(
        self,
        data,
        target_value,
        mode: SearchMode = SearchMode.EXACT,
        value_types=None,
        max_results=None,
        min_depth=0,
        max_depth=None,
    ) -> List[SearchResult]:
        """Search for values in JSON data with various matching modes."""
        self.results = []
        self._search_values_recursive(
            data, target_value, mode, "root", 0, value_types, min_depth, max_depth
        )

        if max_results:
            self.results = self.results[:max_results]

        return self.results

    def search_key_value_pairs(
        self,
        data,
        key_pattern,
        value_pattern,
        key_mode=SearchMode.EXACT,
        value_mode=SearchMode.EXACT,
    ) -> List[SearchResult]:
        """Search for key-value pairs matching both patterns."""
        self.results = []
        self._search_pairs_recursive(
            data, key_pattern, value_pattern, key_mode, value_mode, "root", 0
        )
        return self.results

    def search_with_filter(
        self,
        data,
        filter_func,
        path="root",
        depth=0,
    ) -> List[SearchResult]:
        """Search using a custom filter function."""
        self.results = []
        self._search_with_filter_recursive(data, filter_func, path, depth)
        return self.results

    def _search_keys_recursive(
        self,
        data,
        target_key,
        mode,
        path,
        depth,
        min_depth,
        max_depth,
    ):
        """Recursive key search implementation."""
        if max_depth is not None and depth > max_depth:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}"

                # Check if key matches and depth is within range
                if depth >= min_depth and self._matches(key, target_key, mode):
                    result = SearchResult(
                        path=new_path, value=value, parent_key=key, depth=depth
                    )
                    self.results.append(result)

                # Continue searching in nested structures
                self._search_keys_recursive(
                    value, target_key, mode, new_path, depth + 1, min_depth, max_depth
                )

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                new_path = f"{path}[{idx}]"
                self._search_keys_recursive(
                    item, target_key, mode, new_path, depth + 1, min_depth, max_depth
                )

    def _search_values_recursive(
        self,
        data,
        target_value,
        mode,
        path,
        depth,
        value_types,
        min_depth,
        max_depth,
    ):
        """Recursive value search implementation."""
        if max_depth is not None and depth > max_depth:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}"
                self._search_values_recursive(
                    value,
                    target_value,
                    mode,
                    new_path,
                    depth + 1,
                    value_types,
                    min_depth,
                    max_depth,
                )

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                new_path = f"{path}[{idx}]"
                self._search_values_recursive(
                    item,
                    target_value,
                    mode,
                    new_path,
                    depth + 1,
                    value_types,
                    min_depth,
                    max_depth,
                )
        else:
            # Check if this is a leaf value that matches criteria
            if depth >= min_depth:
                if value_types is None or type(data) in value_types:
                    if self._matches(data, target_value, mode):
                        result = SearchResult(path=path, value=data, depth=depth)
                        self.results.append(result)

    def _search_pairs_recursive(
        self,
        data,
        key_pattern,
        value_pattern,
        key_mode,
        value_mode,
        path,
        depth,
    ):
        """Recursive key-value pair search implementation."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}"

                # Check if both key and value match
                if self._matches(key, key_pattern, key_mode) and self._matches(
                    value, value_pattern, value_mode
                ):
                    result = SearchResult(
                        path=new_path, value=value, parent_key=key, depth=depth
                    )
                    self.results.append(result)

                # Continue searching in nested structures
                self._search_pairs_recursive(
                    value,
                    key_pattern,
                    value_pattern,
                    key_mode,
                    value_mode,
                    new_path,
                    depth + 1,
                )

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                new_path = f"{path}[{idx}]"
                self._search_pairs_recursive(
                    item,
                    key_pattern,
                    value_pattern,
                    key_mode,
                    value_mode,
                    new_path,
                    depth + 1,
                )

    def _search_with_filter_recursive(
        self,
        data,
        filter_func,
        path,
        depth,
    ):
        """Recursive search with custom filter function."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}"

                if filter_func(key, value, depth):
                    result = SearchResult(
                        path=new_path, value=value, parent_key=key, depth=depth
                    )
                    self.results.append(result)

                self._search_with_filter_recursive(
                    value, filter_func, new_path, depth + 1
                )

        elif isinstance(data, list):
            for idx, item in enumerate(data):
                new_path = f"{path}[{idx}]"
                self._search_with_filter_recursive(
                    item, filter_func, new_path, depth + 1
                )

    def _matches(self, actual: Any, target: Any, mode: SearchMode):
        """Check if actual value matches target based on mode."""
        try:
            if mode == SearchMode.EXACT:
                return actual == target

            # Convert to strings for text-based matching
            actual_str = str(actual)
            target_str = str(target)

            if mode == SearchMode.CASE_INSENSITIVE:
                return actual_str.lower() == target_str.lower()
            elif mode == SearchMode.CONTAINS:
                return target_str in actual_str
            elif mode == SearchMode.STARTSWITH:
                return actual_str.startswith(target_str)
            elif mode == SearchMode.ENDSWITH:
                return actual_str.endswith(target_str)
            elif mode == SearchMode.REGEX:
                return bool(re.search(target_str, actual_str))

            return False
        except (TypeError, AttributeError):
            return False

    def print_results(self, results=None, show_tree=False, mode=None):
        """Print search results in a formatted table or tree."""
        results = results or self.results

        if mode:
            self.console.print(f"⚙️ Search mode: [yellow]{mode}\n[/yellow]")

        if not results:
            self.console.print("[yellow]No results found.[/yellow]")
            return

        if show_tree:
            self._print_results_tree(results)
        else:
            self._print_results_table(results)

    def _print_results_table(self, results):
        """Print results in a table format."""
        table = Table(title=f"Search Results ({len(results)} found)")
        table.add_column("Path", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Depth", style="blue", justify="center")

        for result in results:
            # Truncate long values for display
            value_str = str(result.value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."

            table.add_row(result.path, value_str, result.data_type, str(result.depth))

        self.console.print(table)

    def _print_results_tree(self, results):
        """Print results in a tree format."""
        tree = Tree("[bold blue]Search Results[/bold blue]")

        for result in results:
            value_str = str(result.value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."

            node_text = f"[cyan]{result.path}[/cyan] = [green]{value_str}[/green] [dim]({result.data_type})[/dim]"
            tree.add(node_text)

        self.console.print(tree)


if __name__ == "__main__":
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice Johnson",
                "email": "alice@example.com",
                "profile": {
                    "age": 30,
                    "settings": {
                        "theme": "dark",
                        "notifications": True,
                        "language": "en",
                    },
                },
                "tags": ["admin", "user"],
            },
            {
                "id": 2,
                "name": "Bob Smith",
                "email": "bob@company.com",
                "profile": {
                    "age": 25,
                    "settings": {"theme": "light", "notifications": False},
                },
                "tags": ["user"],
            },
        ],
        "metadata": {
            "total_users": 2,
            "created_date": "2024-01-01",
            "settings_version": "1.0",
        },
    }

    searcher = JsonSearcher()

    rprint("\n[bold]🔍 Searching for keys containing 'settings':[/bold]")
    results = searcher.search_keys(test_data, "settings", SearchMode.CONTAINS)
    searcher.print_results(results)

    rprint("\n[bold]🔍 Searching for values containing '@':[/bold]")
    results = searcher.search_values(
        test_data, "@", SearchMode.CONTAINS, value_types={str}
    )
    searcher.print_results(results)

    rprint(
        "\n[bold]🔍 Searching for 'key' = 'tags' and values containing 'user':[/bold]"
    )
    results = searcher.search_key_value_pairs(
        test_data,
        key_pattern="tags",
        value_pattern="user",
        value_mode=SearchMode.CONTAINS,
    )
    searcher.print_results(results, mode=SearchMode.CONTAINS)

    rprint("\n[bold]🔍 Custom search for numeric values > 10:[/bold]")
    results = searcher.search_with_filter(
        test_data,
        lambda key, value, depth: isinstance(value, (int, float)) and value > 10,
    )
    searcher.print_results(results, show_tree=True)
