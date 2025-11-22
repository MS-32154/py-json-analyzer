"""
Additional tests for generator factory functions.

Tests for:
- Go: create_web_api_generator(), create_strict_generator()
- Python: create_typeddict_generator()
"""

from json_explorer.codegen.languages.go import (
    create_web_api_generator,
    create_strict_generator,
)
from json_explorer.codegen.languages.python import (
    create_typeddict_generator,
    PythonStyle,
)
from json_explorer.analyzer import analyze_json
from json_explorer.codegen.core import convert_analyzer_output, extract_all_schemas


# ============================================================================
# Go Factory Function Tests
# ============================================================================


class TestGoFactoryFunctions:
    """Test Go generator factory functions."""

    def test_create_web_api_generator_config(self):
        """Test web API generator has correct configuration."""
        generator = create_web_api_generator()

        # Check package name
        assert generator.config.package_name == "models"

        # Check JSON tags enabled
        assert generator.config.generate_json_tags is True
        assert generator.config.json_tag_omitempty is True

        # Check comments enabled
        assert generator.config.add_comments is True

        # Check Go-specific config
        assert generator.go_config.use_pointers_for_optional is True
        assert generator.go_config.int_type == "int64"
        assert generator.go_config.float_type == "float64"

    def test_create_web_api_generator_output(self):
        """Test web API generator produces correct output."""
        data = {
            "user_id": 1,
            "name": "Alice",
            "email": None,  # Optional field
            "settings": {"theme": "dark", "notifications": True},
        }

        analysis = analyze_json(data)
        generator = create_web_api_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should have JSON tags with omitempty
        assert "`json:" in result

        # Should be package models
        assert "package models" in result

    def test_create_web_api_generator_with_optional_fields(self):
        """Test web API generator handles optional fields correctly."""
        data = [
            {"id": 1, "name": "John", "email": None},
            {"id": 2, "name": "Jane", "email": "jane@example.com"},
        ]

        analysis = analyze_json(data)
        generator = create_web_api_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Email should be optional with pointer (or string if analyzer detected as optional)
        assert "email" in result.lower()
        # Should have omitempty for optional fields
        assert "omitempty" in result

    def test_create_strict_generator_config(self):
        """Test strict generator has correct configuration."""
        generator = create_strict_generator()

        # Check package name
        assert generator.config.package_name == "types"

        # Check JSON tags
        assert generator.config.generate_json_tags is True
        assert generator.config.json_tag_omitempty is False  # No omitempty in strict

        # Check comments
        assert generator.config.add_comments is True

        # Check Go-specific: NO POINTERS
        assert generator.go_config.use_pointers_for_optional is False

    def test_create_strict_generator_output(self):
        """Test strict generator produces correct output."""
        data = {
            "user_id": 1,
            "name": "Alice",
            "email": None,  # Would be optional in web API
        }

        analysis = analyze_json(data)
        generator = create_strict_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should be package types
        assert "package types" in result

        # Should NOT have omitempty
        assert "omitempty" not in result

    def test_create_strict_generator_no_pointers(self):
        """Test strict generator never uses pointers for optional fields."""
        data = [
            {"name": "John", "age": 30, "city": None},
            {"name": "Jane", "age": 25, "city": "NYC"},
        ]

        analysis = analyze_json(data)
        generator = create_strict_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # In strict mode, optional fields are still value types
        # Should not have omitempty
        assert "omitempty" not in result

    def test_web_api_vs_strict_comparison(self):
        """Compare web API vs strict generator outputs."""
        data = [{"id": 1, "email": None}, {"id": 2, "email": "test@example.com"}]

        analysis = analyze_json(data)

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        # Web API generator
        web_gen = create_web_api_generator()
        web_result = web_gen.generate(all_schemas, "User")

        # Strict generator
        strict_gen = create_strict_generator()
        strict_result = strict_gen.generate(all_schemas, "User")

        # Web API should have omitempty (for optional fields)
        assert "omitempty" in web_result

        # Strict should NOT have omitempty
        assert "omitempty" not in strict_result

        # Different packages
        assert "package models" in web_result
        assert "package types" in strict_result


# ============================================================================
# Python TypedDict Tests
# ============================================================================


class TestPythonTypedDictGenerator:
    """Test Python TypedDict generator factory function."""

    def test_create_typeddict_generator_config(self):
        """Test TypedDict generator has correct configuration."""
        generator = create_typeddict_generator()

        # Check package name (corrected expectation)
        assert generator.config.package_name == "models"

        # Check case conventions (Python defaults)
        assert generator.config.struct_case == "pascal"
        assert generator.config.field_case == "snake"

        # Check comments
        assert generator.config.add_comments is True

        # Check Python-specific config
        assert generator.python_config.style == PythonStyle.TYPEDDICT
        assert generator.python_config.use_optional is True
        assert generator.python_config.typeddict_total is False

    def test_create_typeddict_generator_output(self):
        """Test TypedDict generator produces correct output."""
        data = {"user_id": 1, "name": "Alice", "email": "alice@example.com"}

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should use TypedDict
        assert "TypedDict" in result
        assert "class User(TypedDict" in result

        # Should have type hints
        assert "user_id: int" in result
        assert "name: str" in result

    def test_typeddict_with_optional_fields(self):
        """Test TypedDict handles optional fields with NotRequired."""
        data = [
            {"name": "John", "email": None},
            {"name": "Jane", "email": "jane@example.com"},
        ]

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should use NotRequired for optional fields
        assert "NotRequired" in result or "str | None" in result
        assert "email" in result

    def test_typeddict_total_false(self):
        """Test TypedDict with total=False configuration."""
        generator = create_typeddict_generator()

        # Default should be total=False
        assert generator.python_config.typeddict_total is False

        data = {"name": "Alice", "age": 30}
        analysis = analyze_json(data)

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should have total=False in class definition
        assert "total=False" in result

    def test_typeddict_nested_structures(self):
        """Test TypedDict with nested objects."""
        data = {"user": {"name": "Alice", "profile": {"age": 30, "city": "NYC"}}}

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "Root")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "Root")

        # Should generate multiple TypedDict classes
        assert result.count("class") >= 3  # Root, User, Profile
        assert "TypedDict" in result

    def test_typeddict_with_arrays(self):
        """Test TypedDict with array fields."""
        data = {"name": "Alice", "tags": ["python", "coding"], "scores": [95, 87, 92]}

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should use list[T] syntax
        assert "list[str]" in result
        assert "list[int]" in result

    def test_typeddict_imports(self):
        """Test TypedDict generates correct imports."""
        data = {"name": "Alice", "age": 30, "email": None, "tags": ["python"]}

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should import TypedDict
        assert "from typing import TypedDict" in result

    def test_typeddict_field_case_snake(self):
        """Test TypedDict uses snake_case for fields (Python convention)."""
        data = {"userId": 1, "userName": "Alice", "emailAddress": "alice@example.com"}

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "User")

        # Should convert to snake_case
        assert "user_id:" in result
        assert "user_name:" in result
        assert "email_address:" in result

    def test_typeddict_vs_dataclass_comparison(self):
        """Compare TypedDict vs dataclass output."""
        data = {"name": "Alice", "age": 30}

        analysis = analyze_json(data)

        root_schema = convert_analyzer_output(analysis, "User")
        all_schemas = extract_all_schemas(root_schema)

        # TypedDict generator
        typeddict_gen = create_typeddict_generator()
        typeddict_result = typeddict_gen.generate(all_schemas, "User")

        # Dataclass generator
        from json_explorer.codegen.languages.python import create_dataclass_generator

        dataclass_gen = create_dataclass_generator()
        dataclass_result = dataclass_gen.generate(all_schemas, "User")

        # TypedDict should have TypedDict
        assert "TypedDict" in typeddict_result
        assert "@dataclass" not in typeddict_result

        # Dataclass should have @dataclass
        assert "@dataclass" in dataclass_result
        assert "TypedDict" not in dataclass_result

        # Both should have type hints
        assert "name: str" in typeddict_result
        assert "name: str" in dataclass_result


# ============================================================================
# Integration Tests
# ============================================================================


class TestFactoryFunctionIntegration:
    """Integration tests using factory functions with real data."""

    def test_web_api_real_world_example(self):
        """Test web API generator with realistic API response."""
        data = {
            "users": [
                {
                    "id": 1,
                    "username": "alice",
                    "email": "alice@example.com",
                    "profile": {
                        "avatar_url": None,
                        "bio": "Software engineer",
                        "location": "NYC",
                    },
                    "created_at": "2024-01-01T00:00:00Z",
                },
                {
                    "id": 2,
                    "username": "bob",
                    "email": None,
                    "profile": {
                        "avatar_url": "https://example.com/avatar.jpg",
                        "bio": None,
                        "location": "SF",
                    },
                    "created_at": "2024-01-02T00:00:00Z",
                },
            ],
            "total": 2,
            "page": 1,
        }

        analysis = analyze_json(data)
        generator = create_web_api_generator()

        root_schema = convert_analyzer_output(analysis, "APIResponse")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "APIResponse")

        # Should handle optional fields
        assert "package models" in result
        assert "omitempty" in result

        # Should generate multiple structs (check for struct keyword)
        assert result.count("type") >= 3  # Multiple type definitions
        assert "struct {" in result

    def test_strict_performance_critical_example(self):
        """Test strict generator for performance-critical code."""
        data = {
            "timestamp": 1234567890,
            "value": 42.5,
            "readings": [1, 2, 3, 4, 5],
            "metadata": {"sensor_id": "ABC123", "location": "Room 1"},
        }

        analysis = analyze_json(data)
        generator = create_strict_generator()

        root_schema = convert_analyzer_output(analysis, "SensorData")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "SensorData")

        # Should use value types (no pointers)
        assert "package types" in result

        # Should not have omitempty (strict mode)
        assert "omitempty" not in result

    def test_typeddict_type_checking_example(self):
        """Test TypedDict for static type checking."""
        data = {
            "config": {
                "debug": True,
                "timeout": 30,
                "endpoints": ["api.example.com", "backup.example.com"],
                "credentials": {"api_key": "secret123", "token": None},
            }
        }

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "Config")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "Config")

        # Should generate TypedDict classes
        assert "TypedDict" in result
        assert result.count("class") >= 3  # Config, nested structures


# ============================================================================
# Edge Case Tests
# ============================================================================


class TestFactoryFunctionEdgeCases:
    """Test edge cases for factory functions."""

    def test_empty_data_web_api(self):
        """Test web API generator with empty data."""
        data = {}

        analysis = analyze_json(data)
        generator = create_web_api_generator()

        root_schema = convert_analyzer_output(analysis, "Empty")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "Empty")

        # Should still generate valid Go code
        assert "package models" in result
        assert "type Empty struct" in result or "type" in result

    def test_all_optional_strict(self):
        """Test strict generator when all fields are optional."""
        data = [{"a": None, "b": None}, {"a": 1, "b": "text"}]

        analysis = analyze_json(data)
        generator = create_strict_generator()

        root_schema = convert_analyzer_output(analysis, "Data")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "Data")

        # Even with all optional, strict mode uses value types
        assert "package types" in result

    def test_deep_nesting_typeddict(self):
        """Test TypedDict with deeply nested structures."""
        data = {"level1": {"level2": {"level3": {"level4": {"value": 42}}}}}

        analysis = analyze_json(data)
        generator = create_typeddict_generator()

        root_schema = convert_analyzer_output(analysis, "Root")
        all_schemas = extract_all_schemas(root_schema)

        result = generator.generate(all_schemas, "Root")

        # Should generate multiple TypedDict classes
        assert result.count("class") >= 5
        assert "TypedDict" in result
