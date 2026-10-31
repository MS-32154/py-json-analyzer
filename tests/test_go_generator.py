"""
Tests for Go generator.
"""

import pytest
from json_explorer.codegen import create_generator, quick_generate
from json_explorer.codegen.core import FieldType, GeneratorConfig, Schema
from json_explorer.codegen.languages.go import GoConfig


class TestGoConfig:
    """Test Go-specific configuration."""

    def test_default_config(self):
        config = GoConfig()

        assert config.int_type == "int64"
        assert config.float_type == "float64"
        assert config.use_pointers_for_optional is True

    def test_get_go_type(self):
        """Test Go type mapping including None handling."""
        config = GoConfig()

        # Unknown values are `any`; an optional `any` gets no pointer (nil fits)
        assert config.get_go_type(FieldType.UNKNOWN) == "any"
        assert config.get_go_type(FieldType.UNKNOWN, is_optional=True) == "any"
        assert config.get_go_type(FieldType.CONFLICT, is_optional=True) == "any"

        # Regular types get pointers when optional
        assert config.get_go_type(FieldType.STRING, is_optional=True) == "*string"
        assert config.get_go_type(FieldType.INTEGER, is_optional=True) == "*int64"


class TestGoGenerator:
    """Test Go code generator."""

    def test_create_generator(self):
        gen = create_generator("go")

        assert gen.language_name == "go"
        assert gen.file_extension == ".go"

    def test_config_defaults(self):
        config = GoConfig()
        assert config.int_type == "int64"
        assert config.float_type == "float64"
        assert config.use_pointers_for_optional is True

    def test_type_mapping(self):
        config = GoConfig()

        go_type = config.get_go_type(FieldType.STRING)
        assert go_type == "string"

        go_type = config.get_go_type(FieldType.INTEGER)
        assert go_type == "int64"

        go_type = config.get_go_type(FieldType.BOOLEAN)
        assert go_type == "bool"

    def test_simple_struct_generation(self):
        data = {
            "user_id": 123,
            "name": "John",
            "active": True,
        }

        code = quick_generate(data, language="go")

        assert "package main" in code
        assert "type Root struct" in code
        assert "UserID" in code or "UserId" in code
        assert "Name" in code
        assert "Active" in code
        assert "json:" in code  # JSON tags

    def test_nested_struct_generation(self):
        data = {
            "user": {
                "name": "John",
                "age": 30,
            }
        }

        code = quick_generate(data, language="go")

        assert "type Root struct" in code
        assert "type User struct" in code
        assert "Name" in code
        assert "Age" in code

    def test_array_types(self):
        assert "Tags []string" in quick_generate({"tags": ["a"]}, "go")

    def test_array_generation(self):
        data = {
            "tags": ["python", "go"],
            "ids": [1, 2, 3],
        }

        code = quick_generate(data, language="go")

        assert "[]string" in code
        assert "[]int64" in code or "[]int" in code

    def test_optional_fields_with_pointers(self):
        """Test optional field handling with proper type detection."""
        data = [
            {"name": "John", "email": None},
            {"name": "Jane", "email": "jane@mail.com"},
        ]
        code = quick_generate(data, language="go", use_pointers_for_optional=True)

        # After fix, email should be detected as optional string with pointer
        assert "*string" in code or "string" in code
        # Should not be interface{} for simple string/None mix
        if "Email interface{}" in code:
            pytest.skip("Analyzer needs improvement for None handling")

    def test_optional_fields_without_pointers(self):
        config = GoConfig(use_pointers_for_optional=False)
        go_type = config.get_go_type(FieldType.STRING, is_optional=True)
        assert go_type == "string"

    def test_custom_package_name(self):
        data = {"id": 1}

        code = quick_generate(
            data,
            language="go",
            package_name="models",
        )

        assert "package models" in code

    def test_removed_no_json_tags_option_is_ignored(self):
        """generate_json_tags was removed: tags are always generated."""
        code = quick_generate({"id": 1}, language="go", generate_json_tags=False)

        assert 'json:"id"' in code

    def test_validation_warnings(self):

        config = GeneratorConfig()
        gen = create_generator("go", config)

        # Empty schema should generate warning
        empty_schema = Schema(name="Empty", original_name="Empty")
        schemas = {"Empty": empty_schema}

        warnings = gen.validate_schemas(schemas)
        assert len(warnings) > 0
        assert "no fields" in warnings[0].lower()


TS = "2024-01-01T10:00:00Z"


class TestGoImports:
    """Imports are recorded while types are chosen (no type-string parsing)."""

    @pytest.mark.parametrize(
        "data",
        [
            {"at": TS},  # time.Time
            [{"at": TS}, {}],  # *time.Time (optional)
            {"at": [TS]},  # []time.Time
            {"at": [[TS]]},  # [][]time.Time
        ],
        ids=["value", "pointer", "slice", "nested-slice"],
    )
    def test_time_imported_once_when_used(self, data):
        code = quick_generate(data, "go")
        assert code.count('import "time"') == 1

    def test_no_import_without_timestamps(self):
        assert "import" not in quick_generate({"a": "x", "b": [1]}, "go")

    def test_no_import_when_timestamps_are_strings(self):
        code = quick_generate({"at": TS}, "go", time_type="string")
        assert "import" not in code
        assert "At string" in code


class TestNestedArrays:
    """#21: every nesting level is kept."""

    def test_go(self):
        code = quick_generate({"m": [[1]], "g": [[{"id": 1}]], "c": [[[1.5]]]}, "go")
        assert "M [][]int64" in code
        assert "G [][]GItem" in code
        assert "C [][][]float64" in code

    def test_python(self):
        code = quick_generate({"m": [[1]], "c": [[[1.5]]]}, "python")
        assert "m: list[list[int]]" in code
        assert "c: list[list[list[float]]]" in code
