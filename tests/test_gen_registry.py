"""
Tests for generator registry.
"""

from pathlib import Path

import pytest
from json_explorer.codegen.core import (
    CodeGenerator,
    GeneratorConfig,
)
from json_explorer.codegen.languages.go import GoGenerator
from json_explorer.codegen.languages.python import PythonGenerator
from json_explorer.codegen.registry import (
    _ALIASES,
    _GENERATORS,
    RegistryError,
    create_generator,
    get_generator_class,
    get_language_info,
    is_supported,
    list_languages,
    register,
)


class TestRegistry:
    """Test generator registry functions."""

    def test_list_languages(self):
        languages = list_languages()

        assert isinstance(languages, list)
        assert len(languages) > 0
        assert "go" in languages
        assert "python" in languages

    def test_is_supported(self):
        assert is_supported("go") is True
        assert is_supported("python") is True
        assert is_supported("golang") is True  # alias
        assert is_supported("py") is True  # alias
        assert is_supported("nonexistent") is False

    def test_get_language_info(self):
        info = get_language_info("go")

        assert info["name"] == "go"
        assert info["file_extension"] == ".go"
        assert "class" in info
        assert isinstance(info["aliases"], list)

    def test_get_language_info_invalid(self):
        with pytest.raises(RegistryError):
            get_language_info("nonexistent")

    def test_aliases_work(self):
        # Test that aliases resolve correctly
        info_go = get_language_info("go")
        info_golang = get_language_info("golang")

        assert info_go["name"] == info_golang["name"]

    def test_get_generator_class(self):
        go_class = get_generator_class("go")
        assert go_class == GoGenerator

        python_class = get_generator_class("python")
        assert python_class == PythonGenerator

    def test_get_generator_class_with_alias(self):
        go_class = get_generator_class("golang")
        assert go_class == GoGenerator

        py_class = get_generator_class("py")
        assert py_class == PythonGenerator

    def test_create_generator(self):
        config = GeneratorConfig(package_name="test")
        generator = create_generator("go", config)

        assert isinstance(generator, GoGenerator)
        assert generator.config.package_name == "test"

    def test_register_custom_generator(self):
        # Create mock generator
        class MockGenerator(CodeGenerator):
            @property
            def language_name(self):
                return "mock"

            @property
            def file_extension(self):
                return ".mock"

            def get_template_directory(self):
                return Path()

            def generate(self, schemas, root_schema_name):
                return "mock code"

        register("mock", MockGenerator, aliases=["test"])

        assert is_supported("mock")
        assert is_supported("test")

        # Cleanup
        del _GENERATORS["mock"]
        del _ALIASES["test"]


class TestCreateConfig:
    def test_returns_config_with_options(self):
        from json_explorer.codegen import create_config

        assert create_config("python", package_name="models").package_name == "models"

    def test_unknown_language_raises(self):
        from json_explorer.codegen import RegistryError, create_config

        with pytest.raises(RegistryError):
            create_config("cobol")


class TestLanguageNamingConventions:
    """Field/type case is fixed by the target language (options removed in 0.5.0)."""

    def test_python_fields_are_snake_case(self):
        from json_explorer.codegen import quick_generate

        assert "user_name: str" in quick_generate({"userName": "x"}, "python")

    def test_go_fields_are_exported(self):
        from json_explorer.codegen import quick_generate

        assert "UserName string" in quick_generate({"user_name": "x"}, "go")
