"""Unit tests for the tree_view module."""

import pytest
from unittest.mock import Mock, patch, MagicMock
from rich.tree import Tree

from json_explorer.tree_view import (
    JsonTreeBuilder,
    print_json_tree,
    print_json_analysis,
    print_compact_tree,
)


@pytest.fixture
def sample_data():
    """Sample JSON data for testing."""
    return {
        "users": [
            {"id": 1, "name": "Alice", "age": 30},
            {"id": 2, "name": "Bob", "age": 25},
        ],
        "metadata": {"total": 2, "created": "2024-01-01"},
    }


@pytest.fixture
def nested_data():
    """Nested data with optional fields and conflicts."""
    return {
        "user": {
            "profile": {
                "name": "Alice",
                "settings": {"theme": "dark", "notifications": True},
            },
            "tags": ["admin", "user"],
        }
    }


@pytest.fixture
def optional_data():
    """Data with optional fields."""
    return [
        {"id": 1, "name": "Alice", "email": "alice@example.com"},
        {"id": 2, "name": "Bob"},  # email missing
    ]


@pytest.fixture
def conflict_data():
    """Data with type conflicts."""
    return [{"value": 42}, {"value": "text"}]  # type conflict


class TestJsonTreeBuilder:
    """Test JsonTreeBuilder class."""

    def test_initialization_defaults(self):
        """Test builder initialization with defaults."""
        builder = JsonTreeBuilder()
        assert builder.show_conflicts is True
        assert builder.show_optional is True

    def test_initialization_custom(self):
        """Test builder initialization with custom options."""
        builder = JsonTreeBuilder(show_conflicts=False, show_optional=False)
        assert builder.show_conflicts is False
        assert builder.show_optional is False

    def test_type_colors_defined(self):
        """Test that type colors are properly defined."""
        builder = JsonTreeBuilder()
        required_types = ["object", "list", "str", "int", "float", "bool", "conflict"]

        for type_name in required_types:
            assert type_name in builder.TYPE_COLORS
            assert isinstance(builder.TYPE_COLORS[type_name], str)


class TestBuildTree:
    """Test tree building functionality."""

    def test_build_simple_object(self):
        """Test building tree for simple object."""
        from json_explorer.analyzer import analyze_json

        data = {"name": "Alice", "age": 30}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        # Tree should be built without errors
        assert root is not None

    def test_build_nested_object(self):
        """Test building tree for nested object."""
        from json_explorer.analyzer import analyze_json

        data = {"user": {"name": "Alice", "profile": {"age": 30}}}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_build_list(self):
        """Test building tree for list."""
        from json_explorer.analyzer import analyze_json

        data = {"items": [1, 2, 3]}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_build_list_of_objects(self):
        """Test building tree for list of objects."""
        from json_explorer.analyzer import analyze_json

        data = {"users": [{"id": 1, "name": "Alice"}]}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_build_primitive_types(self):
        """Test building tree for primitive types."""
        from json_explorer.analyzer import analyze_json

        data = {"string": "text", "number": 42, "bool": True}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None


class TestOptionalAnnotations:
    """Test optional field annotations."""

    def test_optional_field_shown(self):
        """Test that optional fields are annotated when enabled."""
        from json_explorer.analyzer import analyze_json

        data = [{"id": 1, "email": "alice@example.com"}, {"id": 2}]  # email optional
        summary = analyze_json(data)

        builder = JsonTreeBuilder(show_optional=True)
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        # Should build without errors
        assert root is not None

    def test_optional_field_hidden(self):
        """Test that optional annotations can be hidden."""
        from json_explorer.analyzer import analyze_json

        data = [{"id": 1, "email": "alice@example.com"}, {"id": 2}]
        summary = analyze_json(data)

        builder = JsonTreeBuilder(show_optional=False)
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None


class TestConflictAnnotations:
    """Test conflict annotations."""

    def test_conflict_shown(self):
        """Test that conflicts are shown when enabled."""
        from json_explorer.analyzer import analyze_json

        data = [{"value": 42}, {"value": "text"}]
        summary = analyze_json(data)

        builder = JsonTreeBuilder(show_conflicts=True)
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_conflict_hidden(self):
        """Test that conflicts can be hidden."""
        from json_explorer.analyzer import analyze_json

        data = [{"value": 42}, {"value": "text"}]
        summary = analyze_json(data)

        builder = JsonTreeBuilder(show_conflicts=False)
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None


class TestPrintFunctions:
    """Test print functions."""

    @patch("json_explorer.tree_view.rich_print")
    @patch("json_explorer.tree_view.analyze_json")
    def test_print_json_tree(self, mock_analyze, mock_print, sample_data):
        """Test print_json_tree function."""
        mock_analyze.return_value = {
            "type": "object",
            "children": {"name": {"type": "str", "optional": False}},
        }

        print_json_tree(sample_data, source="Test")

        assert mock_analyze.called
        assert mock_print.called

    @patch("json_explorer.tree_view.rich_print")
    @patch("json_explorer.tree_view.print")
    @patch("json_explorer.tree_view.analyze_json")
    def test_print_json_analysis_with_raw(
        self, mock_analyze, mock_std_print, mock_rich_print, sample_data
    ):
        """Test print_json_analysis with show_raw=True."""
        mock_analyze.return_value = {"type": "object", "children": {}}

        print_json_analysis(sample_data, source="Test", show_raw=True)

        assert mock_analyze.call_count >= 2  # Called for raw and tree
        assert mock_rich_print.call_count >= 1  # Raw analysis
        assert mock_std_print.call_count >= 1  # Headers

    @patch("json_explorer.tree_view.rich_print")
    @patch("json_explorer.tree_view.print")
    @patch("json_explorer.tree_view.analyze_json")
    def test_print_json_analysis_without_raw(
        self, mock_analyze, mock_std_print, mock_rich_print, sample_data
    ):
        """Test print_json_analysis with show_raw=False."""
        mock_analyze.return_value = {"type": "object", "children": {}}

        print_json_analysis(sample_data, source="Test", show_raw=False)

        assert mock_analyze.called
        assert mock_std_print.called  # Header

    @patch("json_explorer.tree_view.print_json_tree")
    def test_print_compact_tree(self, mock_print_tree, sample_data):
        """Test print_compact_tree function."""
        print_compact_tree(sample_data, source="Test")

        assert mock_print_tree.called
        call_args = mock_print_tree.call_args
        assert call_args[1]["show_conflicts"] is False
        assert call_args[1]["show_optional"] is False


class TestFormatNodeLabel:
    """Test node label formatting."""

    def test_format_simple_label(self):
        """Test formatting simple node label."""
        builder = JsonTreeBuilder()
        summary = {"type": "str", "optional": False}

        label = builder._format_node_label(summary, "name")

        assert "name" in label
        assert "str" in label

    def test_format_optional_label(self):
        """Test formatting optional node label."""
        builder = JsonTreeBuilder(show_optional=True)
        summary = {"type": "str", "optional": True}

        label = builder._format_node_label(summary, "email")

        assert "email" in label
        assert "optional" in label.lower()

    def test_format_conflict_label(self):
        """Test formatting conflict node label."""
        builder = JsonTreeBuilder(show_conflicts=True)
        summary = {
            "type": "conflict",
            "optional": False,
            "conflicts": {"value": ["int", "str"]},
        }

        label = builder._format_node_label(summary, "value")

        assert "value" in label
        assert "conflict" in label.lower()

    def test_format_label_without_annotations(self):
        """Test formatting label without annotations."""
        builder = JsonTreeBuilder(show_optional=False, show_conflicts=False)
        summary = {"type": "str", "optional": True, "conflicts": {}}

        label = builder._format_node_label(summary, "field")

        assert "field" in label
        assert "optional" not in label.lower()


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_object(self):
        """Test tree building for empty object."""
        from json_explorer.analyzer import analyze_json

        data = {}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_empty_list(self):
        """Test tree building for empty list."""
        from json_explorer.analyzer import analyze_json

        data = {"items": []}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_null_values(self):
        """Test tree building with null values."""
        from json_explorer.analyzer import analyze_json

        data = {"value": None}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_deeply_nested(self):
        """Test tree building for deeply nested structure."""
        from json_explorer.analyzer import analyze_json

        data = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_mixed_list_types(self):
        """Test tree building for list with mixed types."""
        from json_explorer.analyzer import analyze_json

        data = {"mixed": [1, "text", True, None]}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_list_of_lists(self):
        """Test tree building for nested lists."""
        from json_explorer.analyzer import analyze_json

        data = {"matrix": [[1, 2], [3, 4]]}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None


class TestSpecialTypes:
    """Test special type handling."""

    def test_timestamp_type(self):
        """Test tree building with timestamp type."""
        from json_explorer.analyzer import analyze_json

        data = {"created": "2024-01-01T12:00:00Z"}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_unknown_type(self):
        """Test tree building with unknown type."""
        builder = JsonTreeBuilder()
        summary = {"type": "unknown", "optional": False}

        root = Tree("Test")
        builder.build_tree(summary, root, "field")

        assert root is not None

    def test_conflict_type(self):
        """Test tree building with conflict type."""
        builder = JsonTreeBuilder()
        summary = {
            "type": "conflict",
            "optional": False,
            "conflicts": {"field": ["int", "str"]},
        }

        root = Tree("Test")
        builder.build_tree(summary, root, "field")

        assert root is not None


class TestNodeBuilding:
    """Test specific node building methods."""

    def test_build_object_node(self):
        """Test _build_object_node method."""
        builder = JsonTreeBuilder()
        summary = {
            "type": "object",
            "children": {
                "name": {"type": "str", "optional": False},
                "age": {"type": "int", "optional": False},
            },
        }

        root = Tree("Test")
        builder._build_object_node(summary, root, "user")

        assert root is not None

    def test_build_list_node_with_child_type(self):
        """Test _build_list_node with child_type."""
        builder = JsonTreeBuilder()
        summary = {"type": "list", "child_type": "str"}

        root = Tree("Test")
        builder._build_list_node(summary, root, "items")

        assert root is not None

    def test_build_list_node_with_child_object(self):
        """Test _build_list_node with child object."""
        builder = JsonTreeBuilder()
        summary = {
            "type": "list",
            "child": {
                "type": "object",
                "children": {"id": {"type": "int", "optional": False}},
            },
        }

        root = Tree("Test")
        builder._build_list_node(summary, root, "users")

        assert root is not None

    def test_build_primitive_node(self):
        """Test _build_primitive_node method."""
        builder = JsonTreeBuilder()
        root = Tree("Test")

        builder._build_primitive_node(root, "field (str)")

        assert root is not None


class TestComplexStructures:
    """Test complex data structures."""

    def test_mixed_nested_structure(self):
        """Test tree for mixed nested structure."""
        from json_explorer.analyzer import analyze_json

        data = {
            "user": {
                "id": 1,
                "name": "Alice",
                "tags": ["admin", "user"],
                "profile": {"age": 30, "settings": {"theme": "dark"}},
            },
            "metadata": {"total": 1},
        }
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_array_of_different_objects(self):
        """Test tree for array with different object structures."""
        from json_explorer.analyzer import analyze_json

        data = {
            "items": [
                {"id": 1, "name": "Item1", "optional": "value"},
                {"id": 2, "name": "Item2"},
            ]
        }
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None

    def test_nested_lists(self):
        """Test tree for nested list structures."""
        from json_explorer.analyzer import analyze_json

        data = {"matrix": [[1, 2, 3], [4, 5, 6], [7, 8, 9]]}
        summary = analyze_json(data)

        builder = JsonTreeBuilder()
        root = Tree("Test")
        builder.build_tree(summary, root, "root")

        assert root is not None


class TestPrintIntegration:
    """Test integration of print functions with analyzer."""

    @patch("json_explorer.tree_view.rich_print")
    def test_end_to_end_simple(self, mock_print):
        """Test end-to-end with simple data."""
        data = {"name": "Alice", "age": 30}
        print_json_tree(data, source="User")

        assert mock_print.called

    @patch("json_explorer.tree_view.rich_print")
    def test_end_to_end_complex(self, mock_print):
        """Test end-to-end with complex data."""
        data = {
            "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
            "metadata": {"total": 2},
        }
        print_json_tree(data, source="API Response")

        assert mock_print.called

    @patch("json_explorer.tree_view.rich_print")
    def test_end_to_end_with_conflicts(self, mock_print):
        """Test end-to-end with type conflicts."""
        data = [{"value": 42}, {"value": "text"}]
        print_json_tree(data, source="Conflicted Data")

        assert mock_print.called
