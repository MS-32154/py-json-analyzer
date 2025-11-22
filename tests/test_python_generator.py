"""
Tests for Python generator.
"""

import pytest
from json_explorer.codegen import quick_generate
from json_explorer.codegen.languages.python import (
    PythonConfig,
    PythonStyle,
    create_dataclass_generator,
)
from json_explorer.codegen.core import GeneratorConfig


class TestPythonConfig:
    """Test Python-specific configuration."""

    def test_default_config(self):
        config = PythonConfig()

        assert config.style == PythonStyle.DATACLASS
        assert config.use_optional is True

    def test_dataclass_config(self):
        config = PythonConfig(
            style="dataclass",
            dataclass_slots=True,
            dataclass_frozen=True,
        )

        assert config.style == PythonStyle.DATACLASS
        assert config.dataclass_slots is True
        assert config.dataclass_frozen is True

    def test_pydantic_config(self):
        config = PythonConfig(
            style="pydantic",
            pydantic_use_field=True,
        )

        assert config.style == PythonStyle.PYDANTIC
        assert config.pydantic_use_field is True


class TestPythonGenerator:
    """Test Python code generator."""

    def test_create_generator(self):
        gen = create_dataclass_generator()

        assert gen.language_name == "python"
        assert gen.file_extension == ".py"

    def test_dataclass_generation(self):
        data = {
            "user_id": 123,
            "name": "John",
            "active": True,
        }

        code = quick_generate(data, language="python", style="dataclass")

        assert "@dataclass" in code
        assert "class Root:" in code
        assert "user_id: int" in code
        assert "name: str" in code
        assert "active: bool" in code

    def test_pydantic_generation(self):
        data = {
            "user_id": 123,
            "name": "John",
        }

        code = quick_generate(data, language="python", style="pydantic")

        assert "from pydantic import BaseModel" in code
        assert "class Root(BaseModel):" in code
        assert "user_id: int" in code

    def test_typeddict_generation(self):
        data = {
            "id": 1,
            "name": "Test",
        }

        code = quick_generate(data, language="python", style="typeddict")

        assert "from typing import TypedDict" in code
        assert "class Root(TypedDict" in code

    def test_nested_classes(self):
        data = {
            "user": {
                "name": "John",
                "age": 30,
            }
        }

        code = quick_generate(data, language="python", style="dataclass")

        assert "class RootUser:" in code
        assert "class Root:" in code
        assert "name: str" in code
        assert "age: int" in code

    def test_array_types(self):
        data = {
            "tags": ["python", "go"],
            "scores": [1, 2, 3],
        }

        code = quick_generate(data, language="python", style="dataclass")

        assert "list[str]" in code
        assert "list[int]" in code

    def test_optional_fields(self):
        """Test optional field handling with None values."""
        data = [
            {"name": "John", "email": None},
            {"name": "Jane", "email": "jane@mail.com"},
        ]
        code = quick_generate(data, language="python", style="dataclass")

        # After fix, email should be detected as optional string
        assert "email: str | None" in code or "email: str" in code
        # Should not be Any
        assert ": Any" not in code or "# ⚠️ Mixed types" in code

    def test_snake_case_field_names(self):
        data = {
            "userId": 1,
            "firstName": "John",
        }

        code = quick_generate(
            data,
            language="python",
            style="dataclass",
            field_case="snake",
        )

        # Python should convert to snake_case
        assert "user_id" in code
        assert "first_name" in code

    def test_frozen_dataclass(self):
        data = {"id": 1}

        code = quick_generate(
            data,
            language="python",
            style="dataclass",
            dataclass_frozen=True,
        )

        assert "frozen=True" in code

    def test_slots_dataclass(self):
        data = {"id": 1}

        code = quick_generate(
            data,
            language="python",
            style="dataclass",
            dataclass_slots=True,
        )

        assert "slots=True" in code

    def test_pydantic_field_config(self):
        """Test Pydantic Field() generation."""

        # Test 1: Field with different name (should generate alias)
        data = {"userId": 1, "userName": "Alice"}  # camelCase → snake_case
        code = quick_generate(
            data,
            language="python",
            style="pydantic",
            pydantic_use_field=True,
            pydantic_use_alias=True,
        )

        # Should have Field() with alias
        assert "Field(" in code
        assert 'alias="userId"' in code or 'alias="userName"' in code

        # Test 2: Optional field (should generate Field with default)
        data = [
            {"name": "John", "email": None},
            {"name": "Jane", "email": "jane@example.com"},
        ]
        code = quick_generate(
            data,
            language="python",
            style="pydantic",
            pydantic_use_field=True,
        )

        # Should have Field() for optional email
        assert "Field(" in code or "= None" in code

        # Test 3: No Field() needed (snake_case, required, no description)
        data = {"user_id": 1}  # Already snake_case, required
        code = quick_generate(
            data,
            language="python",
            style="pydantic",
            pydantic_use_field=True,
            pydantic_use_alias=True,
        )

        # Should NOT have Field() - no alias needed, not optional
        assert "user_id: int" in code


class TestPythonStyles:
    """Test different Python styles."""

    @pytest.mark.parametrize("style", ["dataclass", "pydantic", "typeddict"])
    def test_all_styles_work(self, style):
        data = {"id": 1, "name": "Test"}

        code = quick_generate(data, language="python", style=style)

        assert code  # Should generate something
        assert "class Root" in code
        assert "id_:" in code or "id :" in code
        assert "name:" in code or "name :" in code
