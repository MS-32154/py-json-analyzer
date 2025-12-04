"""Advanced JSON search functionality with multiple modes and filtering.

This module provides comprehensive search capabilities for JSON structures,
including key/value searches, pattern matching, and custom filter functions.
"""

import re
from dataclasses import dataclass
from enum import Enum
from typing import Any, Callable

from rich.console import Console
from rich.table import Table
from rich.tree import Tree

from .logging_config import get_logger

logger = get_logger(__name__)


class SearchMode(Enum):
    """Search mode options for pattern matching."""

    EXACT = "exact"
    CONTAINS = "contains"
    REGEX = "regex"
    STARTSWITH = "startswith"
    ENDSWITH = "endswith"
    CASE_INSENSITIVE = "case_insensitive"

    def __str__(self) -> str:
        return self.value

    @classmethod
    def _missing_(cls, value: object) -> "SearchMode | None":
        """Handle missing enum values."""
        for member in cls:
            if member.value == value:
                return member
        return None


@dataclass
class SearchResult:
    """Represents a search result with path and context.

    Attributes:
        path: JSON path to the found item.
        value: The value found.
        parent_key: Key of the parent object (if applicable).
        parent_value: Value of the parent (if applicable).
        depth: Depth in the JSON structure.
        data_type: Type name of the value.
    """

    path: str
    value: Any
    parent_key: str | None = None
    parent_value: Any | None = None
    depth: int = 0
    data_type: str = ""

    def __post_init__(self) -> None:
        """Initialize computed fields."""
        self.data_type = type(self.value).__name__


class JsonSearcher:
    """JSON search utility with multiple search modes and rich output.

    This class provides various search capabilities including key search,
    value search, key-value pair search, and custom filter functions.

    Example:
        >>> searcher = JsonSearcher()
        >>> results = searcher.search_keys(data, "user", SearchMode.CONTAINS)
        >>> searcher.print_results(results)
    """

    def __init__(self, console: Console | None = None) -> None:
        """Initialize the searcher.

        Args:
            console: Optional Rich console for output.
        """
        self.console = console or Console()
        self.results: list[SearchResult] = []
        logger.debug("JsonSearcher initialized")

    def search_keys(
        self,
        data: Any,
        target_key: str,
        mode: SearchMode = SearchMode.EXACT,
        max_results: int | None = None,
        min_depth: int = 0,
        max_depth: int | None = None,
    ) -> list[SearchResult]:
        """Search for keys in JSON data with various matching modes.

        Args:
            data: JSON data to search.
            target_key: Key pattern to search for.
            mode: Search mode for matching.
            max_results: Maximum number of results to return.
            min_depth: Minimum depth to search.
            max_depth: Maximum depth to search.

        Returns:
            List of search results.

        Example:
            >>> results = searcher.search_keys(
            ...     data, "email", SearchMode.CONTAINS, max_results=10
            ... )
        """
        logger.info(f"Searching for key '{target_key}' with mode {mode}")
        self.results = []
        self._search_keys_recursive(
            data, target_key, mode, "root", 0, min_depth, max_depth
        )

        if max_results:
            self.results = self.results[:max_results]

        logger.info(f"Found {len(self.results)} results")
        return self.results

    def search_values(
        self,
        data: Any,
        target_value: Any,
        mode: SearchMode = SearchMode.EXACT,
        value_types: set[type] | None = None,
        max_results: int | None = None,
        min_depth: int = 0,
        max_depth: int | None = None,
    ) -> list[SearchResult]:
        """Search for values in JSON data with various matching modes.

        Args:
            data: JSON data to search.
            target_value: Value pattern to search for.
            mode: Search mode for matching.
            value_types: Optional set of types to filter by.
            max_results: Maximum number of results to return.
            min_depth: Minimum depth to search.
            max_depth: Maximum depth to search.

        Returns:
            List of search results.

        Example:
            >>> # Find all strings containing '@'
            >>> results = searcher.search_values(
            ...     data, "@", SearchMode.CONTAINS, value_types={str}
            ... )
        """
        logger.info(f"Searching for value '{target_value}' with mode {mode}")
        self.results = []
        self._search_values_recursive(
            data, target_value, mode, "root", 0, value_types, min_depth, max_depth
        )

        if max_results:
            self.results = self.results[:max_results]

        logger.info(f"Found {len(self.results)} results")
        return self.results

    def search_key_value_pairs(
        self,
        data: Any,
        key_pattern: str,
        value_pattern: Any,
        key_mode: SearchMode = SearchMode.EXACT,
        value_mode: SearchMode = SearchMode.EXACT,
    ) -> list[SearchResult]:
        """Search for key-value pairs matching both patterns.

        Args:
            data: JSON data to search.
            key_pattern: Key pattern to match.
            value_pattern: Value pattern to match.
            key_mode: Search mode for key matching.
            value_mode: Search mode for value matching.

        Returns:
            List of search results.

        Example:
            >>> # Find all 'status' keys with value 'active'
            >>> results = searcher.search_key_value_pairs(
            ...     data, "status", "active"
            ... )
        """
        logger.info(
            f"Searching for pairs: key='{key_pattern}' ({key_mode}), "
            f"value='{value_pattern}' ({value_mode})"
        )
        self.results = []
        self._search_pairs_recursive(
            data, key_pattern, value_pattern, key_mode, value_mode, "root", 0
        )
        logger.info(f"Found {len(self.results)} results")
        return self.results

    def search_with_filter(
        self,
        data: Any,
        filter_func: Callable[[str, Any, int], bool],
        path: str = "root",
        depth: int = 0,
    ) -> list[SearchResult]:
        """Search using a custom filter function.

        Args:
            data: JSON data to search.
            filter_func: Function that takes (key, value, depth) and returns bool.
            path: Starting path (default: "root").
            depth: Starting depth (default: 0).

        Returns:
            List of search results.

        Example:
            >>> # Find all integers greater than 10
            >>> filter_func = lambda k, v, d: isinstance(v, int) and v > 10
            >>> results = searcher.search_with_filter(data, filter_func)
        """
        logger.info("Searching with custom filter function")
        self.results = []
        self._search_with_filter_recursive(data, filter_func, path, depth)
        logger.info(f"Found {len(self.results)} results")
        return self.results

    def _search_keys_recursive(
        self,
        data: Any,
        target_key: str,
        mode: SearchMode,
        path: str,
        depth: int,
        min_depth: int,
        max_depth: int | None,
    ) -> None:
        """Recursive key search implementation."""
        if max_depth is not None and depth > max_depth:
            return

        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}"

                if depth >= min_depth and self._matches(key, target_key, mode):
                    result = SearchResult(
                        path=new_path, value=value, parent_key=key, depth=depth
                    )
                    self.results.append(result)

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
        data: Any,
        target_value: Any,
        mode: SearchMode,
        path: str,
        depth: int,
        value_types: set[type] | None,
        min_depth: int,
        max_depth: int | None,
    ) -> None:
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
            if depth >= min_depth:
                if value_types is None or type(data) in value_types:
                    if self._matches(data, target_value, mode):
                        result = SearchResult(path=path, value=data, depth=depth)
                        self.results.append(result)

    def _search_pairs_recursive(
        self,
        data: Any,
        key_pattern: str,
        value_pattern: Any,
        key_mode: SearchMode,
        value_mode: SearchMode,
        path: str,
        depth: int,
    ) -> None:
        """Recursive key-value pair search implementation."""
        if isinstance(data, dict):
            for key, value in data.items():
                new_path = f"{path}.{key}"

                if self._matches(key, key_pattern, key_mode) and self._matches(
                    value, value_pattern, value_mode
                ):
                    result = SearchResult(
                        path=new_path, value=value, parent_key=key, depth=depth
                    )
                    self.results.append(result)

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
        data: Any,
        filter_func: Callable[[str, Any, int], bool],
        path: str,
        depth: int,
    ) -> None:
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

    def _matches(self, actual: Any, target: Any, mode: SearchMode) -> bool:
        """Check if actual value matches target based on mode.

        Args:
            actual: Actual value to check.
            target: Target pattern to match.
            mode: Search mode to use.

        Returns:
            True if match found, False otherwise.
        """
        try:
            if mode == SearchMode.EXACT:
                return actual == target

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
        except (TypeError, AttributeError) as e:
            logger.debug(f"Match error: {e}")
            return False

    def print_results(
        self,
        results: list[SearchResult] | None = None,
        show_tree: bool = False,
        mode: SearchMode | None = None,
    ) -> None:
        """Print search results in a formatted table or tree.

        Args:
            results: Results to print (uses self.results if None).
            show_tree: If True, display as tree; otherwise as table.
            mode: Optional search mode to display.
        """
        results = results or self.results

        if mode:
            self.console.print(f"⚙️ Search mode: [yellow]{mode}[/yellow]\n")

        if not results:
            self.console.print("[yellow]No results found.[/yellow]")
            return

        if show_tree:
            self._print_results_tree(results)
        else:
            self._print_results_table(results)

    def _print_results_table(self, results: list[SearchResult]) -> None:
        """Print results in a table format."""
        table = Table(title=f"Search Results ({len(results)} found)")
        table.add_column("Path", style="cyan", no_wrap=True)
        table.add_column("Value", style="green")
        table.add_column("Type", style="yellow")
        table.add_column("Depth", style="blue", justify="center")

        for result in results:
            value_str = str(result.value)
            if len(value_str) > 50:
                value_str = value_str[:47] + "..."

            table.add_row(result.path, value_str, result.data_type, str(result.depth))

        self.console.print(table)

    def _print_results_tree(self, results: list[SearchResult]) -> None:
        """Print results in a tree format."""
        tree = Tree("[bold blue]Search Results[/bold blue]")

        for result in results:
            value_str = str(result.value)
            if len(value_str) > 100:
                value_str = value_str[:97] + "..."

            node_text = (
                f"[cyan]{result.path}[/cyan] = "
                f"[green]{value_str}[/green] "
                f"[dim]({result.data_type})[/dim]"
            )
            tree.add(node_text)

        self.console.print(tree)
