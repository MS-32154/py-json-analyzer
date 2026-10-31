"""Rich tree views of a JSON document's structure."""

from typing import Any, ClassVar

from rich import print as rich_print
from rich.tree import Tree

from .analyzer import Kind, Node, analyze_json


class JsonTreeBuilder:
    """Builds a Rich tree from ``analyze_json()`` output.

    Each node shows its key, type (with the string format, if any) and,
    optionally, whether it is optional and which kinds a mixed value has.
    """

    KIND_COLORS: ClassVar[dict[Kind, str]] = {
        Kind.OBJECT: "bold blue",
        Kind.ARRAY: "bold magenta",
        Kind.STRING: "green",
        Kind.INTEGER: "dark_orange",
        Kind.FLOAT: "dark_orange",
        Kind.BOOLEAN: "yellow",
        Kind.NULL: "dim white",
        Kind.MIXED: "bold red",
    }

    def __init__(self, show_conflicts: bool = True, show_optional: bool = True) -> None:
        self.show_conflicts = show_conflicts
        self.show_optional = show_optional

    def build_tree(self, node: Node | None, parent: Tree, name: str = "root") -> None:
        """Add ``node`` (and everything below it) to ``parent``."""
        branch = parent.add(self.format_label(node, name))
        if node is None:
            return
        if node.kind == Kind.OBJECT:
            for key in sorted(node.fields):
                self.build_tree(node.fields[key], branch, key)
        elif node.kind == Kind.ARRAY:
            self.build_tree(node.items, branch, "item")

    def format_label(self, node: Node | None, name: str) -> str:
        """``name (type)`` plus optional/mixed annotations."""
        if node is None:  # an array that was always empty
            return f"{name} [dim](unknown)[/dim]"
        color = self.KIND_COLORS[node.kind]
        type_text = node.kind.value
        if node.format:
            type_text += f", {node.format.value}"
        label = f"{name} [{color}]({type_text})[/{color}]"
        if self.show_optional:
            if node.optional:  # key missing from some objects
                label += " [dim](optional)[/dim]"
            if node.nullable and node.kind != Kind.NULL:
                label += " [dim](nullable)[/dim]"
        if node.kind == Kind.MIXED and self.show_conflicts:
            kinds = ", ".join(sorted(k.value for k in node.kinds))
            label += f" [bold red](mixed: {kinds})[/bold red]"
        return label


def print_json_tree(data: Any, source: str = "JSON", **kwargs: Any) -> None:
    """Print the structure of ``data`` as a tree."""
    root = Tree(f"[bold white]{source}[/bold white]")
    JsonTreeBuilder(**kwargs).build_tree(analyze_json(data), root)
    rich_print(root)


def print_json_analysis(
    data: Any, source: str = "JSON", show_raw: bool = False
) -> None:
    """Print the tree, preceded by the raw analysis if ``show_raw``."""
    if show_raw:
        rich_print(f"\n[bold yellow]Raw Analysis for {source}:[/bold yellow]")
        rich_print(analyze_json(data).to_dict())
        rich_print()
    rich_print(f"[bold yellow]Tree Structure for {source}:[/bold yellow]")
    print_json_tree(data, source)


def print_compact_tree(data: Any, source: str = "JSON") -> None:
    """Print the tree without optional/mixed annotations."""
    print_json_tree(data, source, show_conflicts=False, show_optional=False)
