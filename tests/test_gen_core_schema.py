"""
Tests for core schema representation.
"""

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

    def test_get_field(self):
        schema = Schema(name="User", original_name="User")
        field = Field("id", "id", FieldType.INTEGER)
        schema.add_field(field)

        found = schema.get_field("id")
        assert found is not None
        assert found.name == "id"


class TestConvertAnalyzerOutput:
    """Test analyzer output conversion."""

    def test_simple_object(self):
        analyzer_result = {
            "type": "object",
            "children": {
                "name": {"type": "str", "optional": False},
                "age": {"type": "int", "optional": False},
            },
            "conflicts": {},
        }

        schema = convert_analyzer_output(analyzer_result, "User")

        assert schema.name == "User"
        assert len(schema.fields) == 2
        assert schema.fields[0].type == FieldType.STRING
        assert schema.fields[1].type == FieldType.INTEGER

    def test_nested_object(self):
        analyzer_result = {
            "type": "object",
            "children": {
                "profile": {
                    "type": "object",
                    "children": {
                        "age": {"type": "int", "optional": False},
                    },
                    "conflicts": {},
                },
            },
            "conflicts": {},
        }

        schema = convert_analyzer_output(analyzer_result, "User")

        assert len(schema.fields) == 1
        assert schema.fields[0].type == FieldType.OBJECT
        assert schema.fields[0].nested_schema is not None

    def test_array_of_primitives(self):
        analyzer_result = {
            "type": "object",
            "children": {
                "tags": {
                    "type": "list",
                    "child_type": "str",
                    "optional": False,
                },
            },
            "conflicts": {},
        }

        schema = convert_analyzer_output(analyzer_result, "Data")

        assert schema.fields[0].type == FieldType.ARRAY
        assert schema.fields[0].array_element_type == FieldType.STRING

    def test_extract_all_schemas(self):
        analyzer_result = {
            "type": "object",
            "children": {
                "profile": {
                    "type": "object",
                    "children": {
                        "age": {"type": "int", "optional": False},
                    },
                    "conflicts": {},
                },
            },
            "conflicts": {},
        }

        root_schema = convert_analyzer_output(analyzer_result, "User")
        all_schemas = extract_all_schemas(root_schema)

        assert len(all_schemas) == 2  # User + UserProfile
        assert "User" in all_schemas
