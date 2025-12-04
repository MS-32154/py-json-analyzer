from __future__ import annotations
from typing import Any
from rich.tree import Tree
from rich import print as rich_print

from .analyzer import analyze_json
from .logging_config import get_logger

logger = get_logger(__name__)


class JsonTreeBuilder:
    """Builds Rich tree visualization from JSON analysis summary.

    Supports optional and conflict annotations, as well as type-based coloring.
    """

    TYPE_COLORS: dict[str, str] = {
        "object": "bold blue",
        "list": "bold magenta",
        "str": "green",
        "int": "dark_orange",
        "float": "dark_orange",
        "bool": "yellow",
        "NoneType": "dim white",
        "conflict": "bold red",
    }

    def __init__(self, show_conflicts: bool = True, show_optional: bool = True) -> None:
        """Initialize the tree builder.

        Args:
            show_conflicts: Whether to display conflict information.
            show_optional: Whether to display optional node annotations.
        """
        self.show_conflicts = show_conflicts
        self.show_optional = show_optional
        logger.debug(
            "JsonTreeBuilder initialized (show_conflicts=%s, show_optional=%s)",
            show_conflicts,
            show_optional,
        )

    def build_tree(
        self, summary: dict[str, Any], parent_tree: Tree, name: str = "root"
    ) -> None:
        """Recursively build a Rich tree from analysis summary.

        Args:
            summary: Analysis summary dictionary for the current node.
            parent_tree: Rich Tree object to attach nodes to.
            name: Name of the current node.
        """
        label = self._format_node_label(summary, name)
        node_type = summary.get("type", "unknown")

        logger.debug("Building tree node '%s' of type '%s'", name, node_type)

        if node_type == "object":
            self._build_object_node(summary, parent_tree, label)
        elif node_type == "list":
            self._build_list_node(summary, parent_tree, label)
        else:
            self._build_primitive_node(parent_tree, label)

    def _format_node_label(self, summary: dict[str, Any], name: str) -> str:
        """Format the label for a tree node.

        Args:
            summary: Analysis summary dictionary for the current node.
            name: Node name.

        Returns:
            A formatted string with type, optional, and conflict annotations.
        """
        node_type = summary.get("type", "unknown")
        optional = summary.get("optional", False)
        conflicts = summary.get("conflicts", {})

        color = self.TYPE_COLORS.get(node_type, "white")
        label = f"{name} [{color}]({node_type})[/{color}]"

        if optional and self.show_optional:
            label += " [dim](optional)[/dim]"

        if conflicts and self.show_conflicts:
            conflict_types = (
                ", ".join(conflicts.keys())
                if isinstance(conflicts, dict)
                else str(conflicts)
            )
            label += f" [bold red](conflicts: {conflict_types})[/bold red]"

        logger.debug("Formatted node label for '%s': %s", name, label)
        return label

    def _build_object_node(
        self, summary: dict[str, Any], parent_tree: Tree, label: str
    ) -> None:
        """Build tree node for object type.

        Args:
            summary: Analysis summary for the object node.
            parent_tree: Rich Tree object to attach to.
            label: Node label.
        """
        branch = parent_tree.add(label)
        children = summary.get("children", {})
        for key in sorted(children.keys()):
            child_summary = children[key]
            self.build_tree(child_summary, branch, key)

    def _build_list_node(
        self, summary: dict[str, Any], parent_tree: Tree, label: str
    ) -> None:
        """Build tree node for list type.

        Args:
            summary: Analysis summary for the list node.
            parent_tree: Rich Tree object to attach to.
            label: Node label.
        """
        branch = parent_tree.add(label)
        if "child" in summary:
            self.build_tree(summary["child"], branch, "item")
        else:
            child_type = summary.get("child_type", "unknown")
            color = self.TYPE_COLORS.get(child_type, "green")
            branch.add(f"item [{color}]({child_type})[/{color}]")

    def _build_primitive_node(self, parent_tree: Tree, label: str) -> None:
        """Build tree node for primitive types.

        Args:
            parent_tree: Rich Tree object to attach to.
            label: Node label.
        """
        parent_tree.add(label)
        logger.debug("Added primitive node: %s", label)


def print_json_tree(data: Any, source: str = "JSON", **kwargs: Any) -> None:
    """Print a Rich tree visualization of JSON structure.

    Args:
        data: The JSON data to analyze.
        source: Name or source of the data for the root label.
        **kwargs: Additional options for JsonTreeBuilder.
    """
    summary = analyze_json(data)
    builder = JsonTreeBuilder(**kwargs)

    root_label = f"[bold white]{source}[/bold white]"
    root = Tree(root_label)
    builder.build_tree(summary, root, "root")
    rich_print(root)


def print_json_analysis(
    data: Any, source: str = "JSON", show_raw: bool = False
) -> None:
    """Print both tree visualization and optionally raw analysis.

    Args:
        data: The JSON data to analyze.
        source: Name or source of the data.
        show_raw: Whether to also print the raw analysis dictionary.
    """
    if show_raw:
        logger.info("Printing raw JSON analysis for source: %s", source)
        print(f"\n[bold yellow]Raw Analysis for {source}:[/bold yellow]")
        summary = analyze_json(data)
        rich_print(summary)
        print()

    logger.info("Printing tree structure for source: %s", source)
    print(f"[bold yellow]Tree Structure for {source}:[/bold yellow]")
    print_json_tree(data, source)


def print_compact_tree(data: Any, source: str = "JSON") -> None:
    """Print tree without optional/conflict annotations for a cleaner view.

    Args:
        data: The JSON data to analyze.
        source: Name or source of the data.
    """
    logger.info("Printing compact tree for source: %s", source)
    print_json_tree(data, source, show_conflicts=False, show_optional=False)


if __name__ == "__main__":
    test_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "profile": {
                    "age": 30,
                    "settings": {"theme": "dark", "notifications": True},
                },
                "tags": ["admin", "user"],
            },
            {
                "id": 2,
                "name": "Bob",
                "profile": {
                    "age": 25,
                    "settings": {
                        "theme": "light",
                        "notifications": False,
                        "language": "en",
                    },
                },
                "tags": ["user"],
                "email": "bob@example.com",
            },
        ],
        "metadata": {"total": 2, "created": "2024-01-01"},
    }

    print_json_analysis(test_data, "Sample Data")
    print("\n" + "=" * 50 + "\n")
    print_compact_tree(test_data, "Sample Data (Compact)")
