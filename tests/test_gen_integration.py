"""
Integration tests for codegen module.
"""

import pytest
from json_explorer.codegen import (
    quick_generate,
    generate_from_analysis,
    create_config,
)
from json_explorer.analyzer import analyze_json


class TestQuickGenerate:
    """Test quick_generate function."""

    def test_quick_generate_go(self):
        data = {"id": 1, "name": "Test"}
        code = quick_generate(data, "go")

        assert "package main" in code
        assert "type Root struct" in code

    def test_quick_generate_python(self):
        data = {"id": 1, "name": "Test"}
        code = quick_generate(data, "python")

        assert "@dataclass" in code
        assert "class Root:" in code

    def test_quick_generate_with_options(self):
        data = {"id": 1}
        code = quick_generate(
            data,
            "go",
            package_name="models",
            add_comments=False,
        )

        assert "package models" in code

    def test_quick_generate_invalid_language(self):
        from json_explorer.codegen.registry import RegistryError

        data = {"id": 1}
        with pytest.raises(RegistryError):
            quick_generate(data, "invalid_language")


class TestGenerateFromAnalysis:
    """Test generate_from_analysis function."""

    def test_generate_from_analysis(self):
        data = {"user_id": 1, "name": "John"}
        analysis = analyze_json(data)

        result = generate_from_analysis(analysis, "go")

        assert result.success is True
        assert result.code
        assert "package main" in result.code
        assert result.metadata["language"] == "go"

    def test_custom_root_name(self):
        data = {"id": 1}
        analysis = analyze_json(data)

        result = generate_from_analysis(analysis, "go", root_name="User")

        assert "type User struct" in result.code

    def test_with_config(self):
        data = {"id": 1}
        analysis = analyze_json(data)
        config = create_config("go", package_name="types")

        result = generate_from_analysis(analysis, "go", config)

        assert "package types" in result.code


class TestComplexDataStructures:
    """Test generation with complex data structures."""

    def test_deeply_nested(self):
        data = {"user": {"profile": {"settings": {"theme": "dark"}}}}

        code = quick_generate(data, "go")

        assert "type Root struct" in code
        assert "type RootUser" in code
        assert "type RootUserProfile" in code

    def test_array_of_objects(self):
        data = {
            "users": [
                {"id": 1, "name": "John"},
                {"id": 2, "name": "Jane"},
            ]
        }

        code = quick_generate(data, "go")

        assert "[]" in code  # Array type

    def test_mixed_types(self):
        data = {
            "id": 123,
            "name": "Test",
            "active": True,
            "score": 98.5,
            "tags": ["a", "b"],
        }

        # Go
        go_code = quick_generate(data, "go")
        assert "int64" in go_code or "int" in go_code
        assert "string" in go_code
        assert "bool" in go_code
        assert "float64" in go_code

        # Python
        py_code = quick_generate(data, "python")
        assert "int" in py_code
        assert "str" in py_code
        assert "bool" in py_code
        assert "float" in py_code


class TestCaseConventions:
    """Test naming case conventions."""

    def test_go_pascal_case(self):
        data = {"user_name": "John", "user-id": 123}

        code = quick_generate(data, "go")

        # Go should use PascalCase
        assert "UserName" in code
        assert "UserId" in code or "UserID" in code

    def test_python_snake_case(self):
        data = {"userName": "John", "userId": 123}

        code = quick_generate(data, "python", style="dataclass", field_case="snake")

        # Python should use snake_case for fields
        assert "user_name" in code
        assert "user_id" in code

    def test_custom_case_style(self):
        data = {"user_name": "John"}

        code = quick_generate(
            data,
            "go",
            struct_case="pascal",
            field_case="camel",
        )

        # Should respect custom case (if implemented)
        assert "struct" in code


class TestEdgeCases:
    """Test edge cases."""

    def test_empty_object(self):
        data = {}

        code = quick_generate(data, "go")
        assert "type Root struct" in code

    def test_single_primitive(self):
        data = {"value": 42}

        code = quick_generate(data, "go")
        assert "type Root struct" in code

    def test_null_values(self):
        data = {"name": "John", "email": None}

        code = quick_generate(data, "go")
        # Should handle optional/nullable fields
        assert code
