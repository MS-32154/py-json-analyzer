"""JMESPath-based JSON search functionality.

This module provides JSON search capabilities using JMESPath query language,
which offers powerful and declarative JSON querying.
"""

from dataclasses import dataclass
from typing import Any

import jmespath
from jmespath.exceptions import JMESPathError
from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class SearchResult:
    """Represents a search result with path and context.

    Attributes:
        path: JSON path expression used.
        value: The value(s) found.
        query: Original JMESPath query.
        data_type: Type name of the value.
    """

    path: str
    value: Any
    query: str
    data_type: str = ""

    def __post_init__(self) -> None:
        """Initialize computed fields."""
        self.data_type = type(self.value).__name__


class JsonSearcher:
    """JMESPath-based JSON search utility with rich output.

    This class provides JSON search capabilities using JMESPath query language,
    which is more powerful and standardized than custom search implementations.

    Example:
        >>> searcher = JsonSearcher()
        >>> result = searcher.search(data, "users[?age > `30`].name")
        >>> searcher.print_result(result)
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the searcher.

        Args:
            console: Optional Rich console for output.
        """
        self.console = console or Console()
        logger.debug("JsonSearcher initialized")

    def search(
        self,
        data: Any,
        query: str,
        compile_query: bool = False,
    ) -> SearchResult | None:
        """Search JSON data using JMESPath query.

        Args:
            data: JSON data to search.
            query: JMESPath query expression.
            compile_query: If True, compile query for better performance
                          when running same query multiple times.

        Returns:
            SearchResult object or None if query fails.

        Example:
            >>> # Simple path
            >>> result = searcher.search(data, "users[0].name")

            >>> # Filter with condition
            >>> result = searcher.search(data, "users[?age > `30`]")

            >>> # Projection
            >>> result = searcher.search(data, "users[*].email")

            >>> # Complex query
            >>> result = searcher.search(
            ...     data,
            ...     "users[?age > `30`].{name: name, email: email}"
            ... )
        """
        logger.info(f"Executing JMESPath query: {query}")

        try:
            if compile_query:
                compiled = jmespath.compile(query)
                result_value = compiled.search(data)
            else:
                result_value = jmespath.search(query, data)

            if result_value is None:
                logger.info("Query returned no results")
                return None

            result = SearchResult(path=query, value=result_value, query=query)
            logger.info(f"Query successful, result type: {result.data_type}")
            return result

        except JMESPathError as e:
            logger.error(f"JMESPath query error: {e}")
            self.console.print(f"[red]Query error: {e}[/red]")
            return None
        except Exception as e:
            logger.error(f"Unexpected error during search: {e}", exc_info=True)
            self.console.print(f"[red]Unexpected error: {e}[/red]")
            return None

    def search_multiple(
        self,
        data: Any,
        queries: list[str],
    ) -> dict[str, SearchResult]:
        """Execute multiple JMESPath queries on the same data.

        Args:
            data: JSON data to search.
            queries: List of JMESPath query expressions.

        Returns:
            Dictionary mapping query strings to SearchResult objects.

        Example:
            >>> queries = [
            ...     "users[*].name",
            ...     "users[?age > `30`]",
            ...     "metadata.total"
            ... ]
            >>> results = searcher.search_multiple(data, queries)
        """
        logger.info(f"Executing {len(queries)} JMESPath queries")
        results = {}

        for query in queries:
            result = self.search(data, query)
            if result is not None:
                results[query] = result

        logger.info(f"Completed {len(results)}/{len(queries)} queries successfully")
        return results

    def validate_query(self, query: str) -> tuple[bool, str | None]:
        """Validate a JMESPath query without executing it.

        Args:
            query: JMESPath query expression to validate.

        Returns:
            Tuple of (is_valid, error_message).

        Example:
            >>> valid, error = searcher.validate_query("users[*].name")
            >>> if not valid:
            ...     print(f"Invalid query: {error}")
        """
        try:
            jmespath.compile(query)
            return True, None
        except JMESPathError as e:
            return False, str(e)
        except Exception as e:
            return False, f"Unexpected error: {e}"

    def print_result(
        self,
        result: SearchResult | None,
        show_tree: bool = False,
        max_display_length: int = 100,
    ) -> None:
        """Print search result in a formatted way.

        Args:
            result: SearchResult to print.
            show_tree: If True, display as tree; otherwise as table.
            max_display_length: Maximum length for displayed values.
        """
        if result is None:
            self.console.print("[yellow]No results found.[/yellow]")
            return

        self.console.print(f"\n[cyan]Query:[/cyan] {result.query}")
        self.console.print(f"[cyan]Result Type:[/cyan] {result.data_type}\n")

        if show_tree:
            self._print_result_tree(result)
        else:
            self._print_result_table(result, max_display_length)

    def _print_result_table(self, result: SearchResult, max_length: int) -> None:
        """Print result in a table format."""

        # For list results, show each item
        if isinstance(result.value, list):
            table = Table(title=f"Results ({len(result.value)} items)")
            table.add_column("Index", style="cyan", justify="center")
            table.add_column("Value", style="green")
            table.add_column("Type", style="yellow")

            for idx, item in enumerate(result.value):
                value_str = str(item)
                if len(value_str) > max_length:
                    value_str = value_str[: max_length - 3] + "..."

                table.add_row(str(idx), value_str, type(item).__name__)

            self.console.print(table)

        # For dict results, show key-value pairs
        elif isinstance(result.value, dict):
            table = Table(title="Result")
            table.add_column("Key", style="cyan")
            table.add_column("Value", style="green")
            table.add_column("Type", style="yellow")

            for key, value in result.value.items():
                value_str = str(value)
                if len(value_str) > max_length:
                    value_str = value_str[: max_length - 3] + "..."

                table.add_row(str(key), value_str, type(value).__name__)

            self.console.print(table)

        # For scalar results, show directly
        else:
            value_str = str(result.value)
            if len(value_str) > max_length:
                value_str = value_str[: max_length - 3] + "..."

            self.console.print(f"[green]{value_str}[/green]")

    def _print_result_tree(self, result: SearchResult) -> None:
        """Print result in a tree format."""
        tree = Tree(f"[bold blue]Query Result[/bold blue]: {result.query}")
        self._add_tree_node(tree, result.value, "result")
        self.console.print(tree)

    def _add_tree_node(self, parent: Tree, value: Any, key: str = "") -> None:
        """Recursively add nodes to tree."""
        if isinstance(value, dict):
            node = parent.add(f"[cyan]{key}[/cyan] [dim](dict)[/dim]")
            for k, v in value.items():
                self._add_tree_node(node, v, k)

        elif isinstance(value, list):
            node = parent.add(f"[cyan]{key}[/cyan] [dim](list)[/dim]")
            for idx, item in enumerate(value):
                self._add_tree_node(node, item, f"[{idx}]")

        else:
            value_str = str(value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."
            parent.add(f"[cyan]{key}[/cyan] = [green]{value_str}[/green]")

    def get_query_examples(self) -> dict[str, str]:
        """Get common JMESPath query examples with descriptions.

        Returns:
            Dictionary mapping descriptions to query examples.
        """
        return {
            "Get all user names": "users[*].name",
            "Filter users over 30": "users[?age > `30`]",
            "Get first user": "users[0]",
            "Get last user": "users[-1]",
            "Select specific fields": "users[*].{name: name, email: email}",
            "Filter and project": "users[?age > `30`].name",
            "Count items": "length(users)",
            "Get nested value": "metadata.created_at",
            "Flatten nested arrays": "users[].tags[]",
            "Filter with contains": "users[?contains(name, 'John')]",
            "Sort by field": "sort_by(users, &age)",
            "Get max value": "max_by(users, &age).name",
            "Multi-condition filter": "users[?age > `30` && active == `true`]",
        }

    def print_examples(self) -> None:
        """Print JMESPath query examples."""
        examples = self.get_query_examples()

        table = Table(title="🔍 JMESPath Query Examples")
        table.add_column("Description", style="cyan")
        table.add_column("Query", style="green")

        for description, query in examples.items():
            table.add_row(description, query)

        self.console.print(table)

        self.console.print("\n[bold]Additional Resources:[/bold]")
        self.console.print("• Tutorial: https://jmespath.org/tutorial.html")
        self.console.print("• Specification: https://jmespath.org/specification.html")
        self.console.print("• Interactive: https://jmespath.org/")
