"""
Tests for core schema representation.
"""

import pytest
from json_explorer.codegen.core.schema import (
    Field,
    FieldType,
    Schema,
    convert_analyzer_output,
    extract_all_schemas,
)


class TestFieldType:
    """Test FieldType enum."""

    def test_field_types_exist(self):
        assert FieldType.STRING.value == "string"
        assert FieldType.INTEGER.value == "integer"
        assert FieldType.ARRAY.value == "array"
        assert FieldType.OBJECT.value == "object"


class TestField:
    """Test Field dataclass."""

    def test_basic_field(self):
        field = Field(
            name="user_id",
            original_name="userId",
            type=FieldType.INTEGER,
        )
        assert field.name == "user_id"
        assert field.type == FieldType.INTEGER
        assert field.optional is False

    def test_optional_field(self):
        field = Field(
            name="email",
            original_name="email",
            type=FieldType.STRING,
            optional=True,
        )
        assert field.optional is True

    def test_array_field(self):
        field = Field(
            name="tags",
            original_name="tags",
            type=FieldType.ARRAY,
            array_element_type=FieldType.STRING,
        )
        assert field.type == FieldType.ARRAY
        assert field.array_element_type == FieldType.STRING


class TestSchema:
    """Test Schema dataclass."""

    def test_basic_schema(self):
        schema = Schema(name="User", original_name="User")
        assert schema.name == "User"
        assert len(schema.fields) == 0

    def test_add_field(self):
        schema = Schema(name="User", original_name="User")
        field = Field("id", "id", FieldType.INTEGER)

        schema.add_field(field)
        assert len(schema.fields) == 1
        assert schema.fields[0].name == "id"


class TestConvertAnalyzerOutput:
    """analyze_json() output -> Schema."""

    @staticmethod
    def convert(data, name="Root"):
        from json_explorer.analyzer import analyze_json

        return convert_analyzer_output(analyze_json(data), name)

    def test_simple_object(self):
        schema = self.convert({"name": "x", "age": 1}, "User")

        assert schema.name == "User"
        assert [f.type for f in schema.fields] == [FieldType.STRING, FieldType.INTEGER]

    def test_nested_object(self):
        schema = self.convert({"profile": {"age": 1}}, "User")

        assert schema.fields[0].type == FieldType.OBJECT
        assert schema.fields[0].nested_schema.name == "Profile"

    def test_array_of_primitives(self):
        fld = self.convert({"tags": ["a"]}).fields[0]

        assert fld.type == FieldType.ARRAY
        assert fld.array_element_type == FieldType.STRING
        assert fld.array_dimensions == 1

    def test_extract_all_schemas(self):
        all_schemas = extract_all_schemas(self.convert({"profile": {"age": 1}}, "User"))

        assert set(all_schemas) == {"User", "Profile"}

    def test_optional_and_null(self):
        schema = self.convert([{"a": 1, "b": None}, {"a": 2, "b": "x"}, {"b": "y"}])
        a, b = schema.fields

        assert (a.type, a.optional) == (FieldType.INTEGER, True)  # missing once
        assert (b.type, b.optional) == (FieldType.STRING, True)  # null once

    def test_int_and_float_widen_to_float(self):
        """#12: 1 and 1.5 are both numbers, not a type conflict."""
        fld = self.convert([{"v": 1}, {"v": 1.5}]).fields[0]

        assert fld.type == FieldType.FLOAT

    def test_mixed_kinds_conflict(self):
        fld = self.convert([{"v": 1}, {"v": "x"}]).fields[0]

        assert fld.type == FieldType.CONFLICT
        assert fld.conflicting_types == [FieldType.INTEGER, FieldType.STRING]

    @pytest.mark.parametrize(
        ("values", "expected"),
        [
            (
                ["2024-01-01T10:00:00Z", "2024-02-01T00:00:00+02:00"],
                FieldType.DATE_TIME,
            ),
            (["2024-01-01T10:00:00"], FieldType.LOCAL_DATE_TIME),
            (["2024-01-01"], FieldType.DATE),
            (["10:30:00"], FieldType.TIME),
            (["PT4H30M", "P1D"], FieldType.DURATION),
            (["2024-01-01", "not a date"], FieldType.STRING),  # all values must match
            (["2024-01-01", "2024-01-01T10:00:00Z"], FieldType.STRING),  # one format
            (["March", "1 hour ago", "10.5"], FieldType.STRING),  # #8
        ],
    )
    def test_string_formats(self, values, expected):
        fld = self.convert([{"v": v} for v in values]).fields[0]

        assert fld.type == expected
