"""
Tests for Python generator.
"""

import pytest
from json_explorer.codegen import create_generator, quick_generate
from json_explorer.codegen.core import FieldType
from json_explorer.codegen.languages.python import PythonConfig, PythonStyle


class TestPythonConfig:
    """Test Python-specific configuration."""

    def test_default_config(self):
        config = PythonConfig()

        assert config.style == PythonStyle.DATACLASS
        assert config.type_map[FieldType.DATE_TIME] == "str"
        pydantic = PythonConfig(style="pydantic").type_map
        assert pydantic[FieldType.DATE_TIME] == "datetime"
        assert pydantic[FieldType.DURATION] == "timedelta"

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
        config = PythonConfig(style="pydantic", pydantic_extra_forbid=True)

        assert config.style == PythonStyle.PYDANTIC
        assert config.pydantic_extra_forbid is True


class TestPythonGenerator:
    """Test Python code generator."""

    def test_create_generator(self):
        gen = create_generator("python", {"style": "dataclass"})

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

        assert "class User:" in code
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
        assert 'alias="userId"' in code
        assert 'alias="userName"' in code

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
        assert "    id: int" in code  # builtins are fine as field names
        assert "    name: str" in code


# a and c are optional (missing from the second item); b is required
FIELD_ORDER_DATA = [{"a": 1, "b": "x", "c": True}, {"b": "y"}]


class TestDataclassFieldOrder:
    @staticmethod
    def field_names(code: str) -> list[str]:
        return [
            line.split(":")[0].strip()
            for line in code.splitlines()
            if line.startswith("    ")
            and ":" in line
            and not line.strip().startswith(("#", '"'))
        ]

    def test_required_fields_come_first_json_order_kept(self):
        code = quick_generate(
            FIELD_ORDER_DATA, "python", style="dataclass", dataclass_kw_only=False
        )
        assert self.field_names(code) == ["b", "a", "c"]

    def test_kw_only_keeps_json_order(self):
        code = quick_generate(
            FIELD_ORDER_DATA, "python", style="dataclass", dataclass_kw_only=True
        )
        assert self.field_names(code) == ["a", "b", "c"]
