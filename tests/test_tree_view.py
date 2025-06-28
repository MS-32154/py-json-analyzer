import unittest
from unittest.mock import patch, MagicMock
from json_explorer.tree_view import (
    JsonTreeBuilder,
    print_json_tree,
    print_json_analysis,
    print_compact_tree,
)


class TestJsonTreeBuilder(unittest.TestCase):

    def setUp(self):
        self.builder = JsonTreeBuilder()

    def test_init_default_options(self):
        builder = JsonTreeBuilder()
        self.assertTrue(builder.show_conflicts)
        self.assertTrue(builder.show_optional)

    def test_init_custom_options(self):
        builder = JsonTreeBuilder(show_conflicts=False, show_optional=False)
        self.assertFalse(builder.show_conflicts)
        self.assertFalse(builder.show_optional)

    def test_format_node_label_basic(self):
        summary = {"type": "str"}
        label = self.builder._format_node_label(summary, "test")
        expected = "test [green](str)[/green]"
        self.assertEqual(label, expected)

    def test_format_node_label_with_optional(self):
        summary = {"type": "str", "optional": True}
        label = self.builder._format_node_label(summary, "test")
        expected = "test [green](str)[/green] [dim](optional)[/dim]"
        self.assertEqual(label, expected)

    def test_format_node_label_with_conflicts(self):
        summary = {"type": "str", "conflicts": {"int": 1}}
        label = self.builder._format_node_label(summary, "test")
        expected = "test [green](str)[/green] [bold red](conflicts: int)[/bold red]"
        self.assertEqual(label, expected)

    def test_format_node_label_hide_optional(self):
        builder = JsonTreeBuilder(show_optional=False)
        summary = {"type": "str", "optional": True}
        label = builder._format_node_label(summary, "test")
        expected = "test [green](str)[/green]"
        self.assertEqual(label, expected)

    def test_format_node_label_hide_conflicts(self):
        builder = JsonTreeBuilder(show_conflicts=False)
        summary = {"type": "str", "conflicts": {"int": 1}}
        label = builder._format_node_label(summary, "test")
        expected = "test [green](str)[/green]"
        self.assertEqual(label, expected)

    def test_type_colors_mapping(self):
        expected_colors = {
            "object": "bold blue",
            "list": "bold magenta",
            "str": "green",
            "int": "dark_orange",
            "float": "dark_orange",
            "bool": "yellow",
            "NoneType": "dim white",
            "conflict": "bold red",
        }
        self.assertEqual(JsonTreeBuilder.TYPE_COLORS, expected_colors)

    @patch("json_explorer.tree_view.Tree")
    def test_build_primitive_node(self, mock_tree_class):
        mock_parent = MagicMock()
        self.builder._build_primitive_node(mock_parent, "test label")
        mock_parent.add.assert_called_once_with("test label")

    @patch("json_explorer.tree_view.Tree")
    def test_build_list_node_with_child_type(self, mock_tree_class):
        mock_parent = MagicMock()
        mock_branch = MagicMock()
        mock_parent.add.return_value = mock_branch

        summary = {"child_type": "str"}
        label = "test [bold magenta](list)[/bold magenta]"

        self.builder._build_list_node(summary, mock_parent, label)

        mock_parent.add.assert_called_once_with(label)
        mock_branch.add.assert_called_once_with("item [green](str)[/green]")

    @patch("json_explorer.tree_view.Tree")
    def test_build_object_node(self, mock_tree_class):
        mock_parent = MagicMock()
        mock_branch = MagicMock()
        mock_parent.add.return_value = mock_branch

        summary = {"children": {"name": {"type": "str"}, "age": {"type": "int"}}}
        label = "test [bold blue](object)[/bold blue]"

        with patch.object(self.builder, "build_tree") as mock_build_tree:
            self.builder._build_object_node(summary, mock_parent, label)

            mock_parent.add.assert_called_once_with(label)
            # Should call build_tree for each child in sorted order
            self.assertEqual(mock_build_tree.call_count, 2)


class TestPrintFunctions(unittest.TestCase):

    @patch("json_explorer.tree_view.print")
    @patch("json_explorer.tree_view.analyze_json")
    @patch("json_explorer.tree_view.Tree")
    def test_print_json_tree(self, mock_tree_class, mock_analyze, mock_print):
        mock_analyze.return_value = {"type": "object"}
        mock_tree_instance = MagicMock()
        mock_tree_class.return_value = mock_tree_instance

        test_data = {"test": "data"}
        print_json_tree(test_data, "Test Source")

        mock_analyze.assert_called_once_with(test_data)
        mock_tree_class.assert_called_once_with("[bold white]Test Source[/bold white]")
        mock_print.assert_called_once_with(mock_tree_instance)

    @patch("json_explorer.tree_view.print")
    @patch("json_explorer.tree_view.analyze_json")
    @patch("json_explorer.tree_view.print_json_tree")
    def test_print_json_analysis_with_raw(
        self, mock_print_tree, mock_analyze, mock_print
    ):
        mock_analyze.return_value = {
            "type": "object",
            "children": {"test": {"type": "str"}},
        }
        test_data = {"test": "data"}

        print_json_analysis(test_data, "Test", show_raw=True)

        # Should print raw analysis and call print_json_tree
        self.assertEqual(
            mock_print.call_count, 4
        )  # Header, raw data, tree header, empty_line
        mock_print_tree.assert_called_once_with(test_data, "Test")

    @patch("json_explorer.tree_view.print_json_tree")
    def test_print_compact_tree(self, mock_print_tree):
        test_data = {"test": "data"}
        print_compact_tree(test_data, "Test")

        mock_print_tree.assert_called_once_with(
            test_data, "Test", show_conflicts=False, show_optional=False
        )


class TestIntegration(unittest.TestCase):

    @patch("json_explorer.tree_view.analyze_json")
    @patch("json_explorer.tree_view.print")
    def test_simple_object_integration(self, mock_print, mock_analyze):
        # Mock the analyzer to return a simple structure
        mock_analyze.return_value = {
            "type": "object",
            "children": {"name": {"type": "str"}, "age": {"type": "int"}},
        }

        test_data = {"name": "Alice", "age": 30}

        # This should not raise any exceptions
        print_json_tree(test_data, "Test")

        mock_analyze.assert_called_once_with(test_data)
        mock_print.assert_called_once()

    @patch("json_explorer.tree_view.analyze_json")
    @patch("json_explorer.tree_view.print")
    def test_simple_list_integration(self, mock_print, mock_analyze):
        mock_analyze.return_value = {"type": "list", "child_type": "str"}

        test_data = ["a", "b", "c"]

        print_json_tree(test_data, "Test")

        mock_analyze.assert_called_once_with(test_data)
        mock_print.assert_called_once()


if __name__ == "__main__":
    unittest.main()
