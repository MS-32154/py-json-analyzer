from rich.tree import Tree
from rich import print
from .analyzer import analyze_json


class JsonTreeBuilder:
    """Builds rich tree visualization from JSON analysis summary."""

    TYPE_COLORS = {
        "object": "bold blue",
        "list": "bold magenta",
        "str": "green",
        "int": "dark_orange",
        "float": "dark_orange",
        "bool": "yellow",
        "NoneType": "dim white",
        "conflict": "bold red",
    }

    def __init__(self, show_conflicts=True, show_optional=True):
        self.show_conflicts = show_conflicts
        self.show_optional = show_optional

    def build_tree(self, summary, parent_tree, name="root"):
        """Recursively build tree from analysis summary."""
        label = self._format_node_label(summary, name)

        node_type = summary.get("type", "unknown")

        if node_type == "object":
            self._build_object_node(summary, parent_tree, label)
        elif node_type == "list":
            self._build_list_node(summary, parent_tree, label)
        else:
            self._build_primitive_node(parent_tree, label)

    def _format_node_label(self, summary, name):
        """Format the label for a tree node."""
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

        return label

    def _build_object_node(self, summary, parent_tree, label):
        """Build tree node for object type."""
        branch = parent_tree.add(label)
        children = summary.get("children", {})

        for key in sorted(children.keys()):
            child_summary = children[key]
            self.build_tree(child_summary, branch, key)

    def _build_list_node(self, summary, parent_tree, label):
        """Build tree node for list type."""
        branch = parent_tree.add(label)

        if "child" in summary:
            self.build_tree(summary["child"], branch, "item")
        else:
            child_type = summary.get("child_type", "unknown")
            color = self.TYPE_COLORS.get(child_type, "green")
            branch.add(f"item [{color}]({child_type})[/{color}]")

    def _build_primitive_node(self, parent_tree, label):
        """Build tree node for primitive types."""
        parent_tree.add(label)


def print_json_tree(data, source="JSON", **kwargs):
    """
    Print a rich tree visualization of JSON structure.

    Args:
        data: The JSON data to analyze
        source: Name/source of the data for the root label
        **kwargs: Additional options for JsonTreeBuilder
    """
    summary = analyze_json(data)
    builder = JsonTreeBuilder(**kwargs)

    root_label = f"[bold white]{source}[/bold white]"
    root = Tree(root_label)

    builder.build_tree(summary, root, "root")
    print(root)


def print_json_analysis(data, source="JSON", show_raw=False):
    """
    Print both tree visualization and optionally raw analysis.

    Args:
        data: The JSON data to analyze
        source: Name/source of the data
        show_raw: Whether to also print the raw analysis dict
    """
    if show_raw:
        print(f"\n[bold yellow]Raw Analysis for {source}:[/bold yellow]")
        summary = analyze_json(data)
        print(summary)
        print()

    print(f"[bold yellow]Tree Structure for {source}:[/bold yellow]")
    print_json_tree(data, source)


def print_compact_tree(data, source="JSON"):
    """Print tree without optional/conflict annotations for cleaner view."""
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
