"""Tests for the Rich tree views."""

import pytest
from json_explorer.analyzer import Kind, analyze_json
from json_explorer.tree_view import (
    JsonTreeBuilder,
    print_compact_tree,
    print_json_analysis,
    print_json_tree,
)
from rich.console import Console
from rich.tree import Tree


def render(data, **options) -> str:
    """Plain-text tree for ``data`` (markup removed)."""
    root = Tree("JSON")
    JsonTreeBuilder(**options).build_tree(analyze_json(data), root)
    console = Console(width=200, color_system=None)
    with console.capture() as captured:
        console.print(root)
    return captured.get()


class TestBuilder:
    def test_defaults(self):
        builder = JsonTreeBuilder()
        assert builder.show_conflicts and builder.show_optional

    def test_every_kind_has_a_color(self):
        assert set(JsonTreeBuilder.KIND_COLORS) == set(Kind)

    def test_object_fields_sorted(self):
        text = render({"b": 1, "a": "x"})
        assert text.index("a (string)") < text.index("b (integer)")

    def test_nested_object_and_array(self):
        text = render({"user": {"tags": ["x"]}})
        assert "user (object)" in text
        assert "tags (array)" in text
        assert "item (string)" in text

    def test_array_of_objects(self):
        text = render([{"id": 1}])
        assert "item (object)" in text
        assert "id (integer)" in text

    def test_empty_array(self):
        assert "item (unknown)" in render({"tags": []})

    def test_nested_arrays(self):
        text = render({"m": [[1]]})
        assert text.count("(array)") == 2
        assert "item (integer)" in text

    def test_formats_shown(self):
        assert "at (string, date-time)" in render({"at": "2024-01-01T10:00:00Z"})

    def test_root_primitive(self):
        assert "root (integer)" in render(5)


# a: missing once (optional); v: integer and string (mixed)
ANNOTATED = [{"a": 1, "v": 1}, {"v": "x"}]


class TestAnnotations:
    def test_optional_shown(self):
        assert "a (integer) (optional)" in render(ANNOTATED)

    def test_optional_hidden(self):
        assert "(optional)" not in render(ANNOTATED, show_optional=False)

    def test_mixed_shown(self):
        assert "v (mixed) (mixed: integer, string)" in render(ANNOTATED)

    def test_mixed_hidden(self):
        text = render(ANNOTATED, show_conflicts=False)
        assert "v (mixed)" in text
        assert "mixed:" not in text

    def test_null_only(self):
        assert "v (null)" in render({"v": None})
        assert "(nullable)" not in render({"v": None})  # implied by null

    def test_nullable_and_optional(self):
        text = render([{"a": None, "b": 1}, {"a": "x"}])
        assert "a (string) (nullable)" in text
        assert "b (integer) (optional)" in text


class TestPrintFunctions:
    @pytest.fixture
    def data(self):
        return {"users": [{"id": 1, "email": None}, {"id": 2, "email": "a@b.c"}]}

    def test_print_json_tree(self, data, capsys):
        print_json_tree(data, "sample")
        out = capsys.readouterr().out
        assert "sample" in out
        assert "email (string) (nullable)" in out

    def test_print_compact_tree(self, data, capsys):
        print_compact_tree(data, "sample")
        assert "(optional)" not in capsys.readouterr().out

    def test_print_json_analysis_raw(self, data, capsys):
        print_json_analysis(data, "sample", show_raw=True)
        out = capsys.readouterr().out
        assert "Raw Analysis for sample" in out
        assert "'kind': 'array'" in out
        assert "[bold yellow]" not in out  # markup is rendered, not printed

    def test_print_json_analysis_without_raw(self, data, capsys):
        print_json_analysis(data, "sample")
        out = capsys.readouterr().out
        assert "Raw Analysis" not in out
        assert "Tree Structure for sample" in out
