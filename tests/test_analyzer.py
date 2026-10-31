"""Tests for the JSON structure analyzer."""

import pytest
from json_explorer.analyzer import (
    Format,
    Kind,
    Node,
    analyze_json,
    detect_format,
    merge,
)


class TestPrimitives:
    @pytest.mark.parametrize(
        ("value", "kind"),
        [
            (5, Kind.INTEGER),
            (2.5, Kind.FLOAT),
            (True, Kind.BOOLEAN),  # bool is not treated as int
            ("hello", Kind.STRING),
            (None, Kind.NULL),
        ],
    )
    def test_kinds(self, value, kind):
        assert analyze_json(value).kind == kind

    def test_null_is_nullable(self):
        node = analyze_json(None)
        assert node.nullable and not node.optional

    def test_not_json(self):
        with pytest.raises(TypeError):
            analyze_json({1, 2})


class TestArrays:
    def test_empty(self):
        assert analyze_json([]) == Node(Kind.ARRAY, items=None)

    def test_primitives(self):
        assert analyze_json([1, 2, 3]).items == Node(Kind.INTEGER)

    def test_int_and_float_widen(self):
        """#12"""
        assert analyze_json([1, 2.5]).items == Node(Kind.FLOAT)

    def test_mixed(self):
        items = analyze_json([1, "a", True]).items
        assert items.kind == Kind.MIXED
        assert items.kinds == {Kind.INTEGER, Kind.STRING, Kind.BOOLEAN}

    def test_null_elements_make_items_nullable(self):
        assert analyze_json([1, None]).items == Node(Kind.INTEGER, nullable=True)

    def test_nested(self):
        items = analyze_json([[1], [], [2, 3]]).items
        assert items.kind == Kind.ARRAY
        assert items.items == Node(Kind.INTEGER)

    def test_every_element_is_used(self):
        """#11: no sampling of the first 20 items."""
        data = [{"a": 1}] * 1000 + [{"a": 1, "late": "x"}]
        fields = analyze_json(data).items.fields
        assert fields["late"] == Node(Kind.STRING, optional=True)
        assert not fields["a"].optional


class TestObjects:
    def test_fields(self):
        node = analyze_json({"name": "x", "age": 1})
        assert node.kind == Kind.OBJECT
        assert node.fields == {"name": Node(Kind.STRING), "age": Node(Kind.INTEGER)}

    def test_missing_keys_are_optional(self):
        fields = analyze_json([{"a": 1, "b": 2}, {"a": 3}]).items.fields
        assert not fields["a"].optional
        assert fields["b"].optional

    def test_null_values_are_nullable_not_missing(self):
        """#23: a null value and a missing key are different things."""
        fields = analyze_json([{"a": None}, {"a": "x"}]).items.fields
        assert fields["a"] == Node(Kind.STRING, nullable=True)

    def test_missing_and_null(self):
        fields = analyze_json([{"a": None}, {"a": "x"}, {}]).items.fields
        assert fields["a"] == Node(Kind.STRING, optional=True, nullable=True)

    def test_only_nulls(self):
        assert analyze_json([{"a": None}]).items.fields["a"] == Node(
            Kind.NULL, nullable=True
        )

    def test_conflict(self):
        fields = analyze_json([{"v": 1}, {"v": "x"}, {"v": None}]).items.fields
        assert fields["v"].kind == Kind.MIXED
        assert fields["v"].kinds == {Kind.INTEGER, Kind.STRING}
        assert fields["v"].nullable

    def test_nested_merge(self):
        data = [{"p": {"x": 1}}, {"p": {"x": 2, "y": "a"}}]
        p = analyze_json(data).items.fields["p"]
        assert p.fields["y"].optional and not p.fields["x"].optional


class TestFormats:
    @pytest.mark.parametrize(
        ("text", "fmt"),
        [
            ("2024-01-01T10:00:00Z", Format.DATE_TIME),
            ("2024-01-01T10:00:00.123+02:00", Format.DATE_TIME),
            ("2024-01-01T10:00:00", Format.LOCAL_DATE_TIME),
            ("2024-01-01", Format.DATE),
            ("10:30:00", Format.TIME),
            ("10:30:00.5Z", Format.TIME),
            ("P3D", Format.DURATION),
            ("PT4H30M", Format.DURATION),
            ("P1DT0.5S", Format.DURATION),
        ],
    )
    def test_detected(self, text, fmt):
        assert detect_format(text) == fmt

    @pytest.mark.parametrize(
        "text",
        [
            "2024-13-45",  # invalid date
            "20240101T100000Z",  # ISO 8601 basic format, not RFC 3339
            "2024-W01-1",  # week date
            "2024-01-01 10:00:00",  # space separator (Go's time.Time rejects it)
            "12:30",  # no seconds
            "P",
            "PT",
            "P1Y",  # years/months have no fixed length
            "March",  # #8: no natural-language parsing
            "Monday",
            "1 hour ago",
            "10.5",
            "",
        ],
    )
    def test_not_detected(self, text):
        assert detect_format(text) is None

    def test_format_needs_every_value(self):
        assert analyze_json(["2024-01-01", "2024-01-02"]).items.format == Format.DATE
        assert analyze_json(["2024-01-01", "soon"]).items.format is None

    def test_merge_keeps_only_common_format(self):
        a = Node(Kind.STRING, format=Format.DATE)
        b = Node(Kind.STRING, format=Format.DATE_TIME)
        assert merge(a, b) == Node(Kind.STRING)


class TestToDict:
    def test_round_trip_shape(self):
        data = [{"id": 1, "at": "2024-01-01", "tags": [], "v": None}, {"id": 2.5}]
        assert analyze_json(data).to_dict() == {
            "kind": "array",
            "items": {
                "kind": "object",
                "fields": {
                    "id": {"kind": "float"},
                    "at": {"kind": "string", "optional": True, "format": "date"},
                    "tags": {"kind": "array", "optional": True, "items": None},
                    "v": {"kind": "null", "optional": True, "nullable": True},
                },
            },
        }
