"""
Tests for generator registry.
"""

import pytest
from pathlib import Path

from json_explorer.codegen.core import (
    GeneratorConfig,
    CodeGenerator,
)

from json_explorer.codegen.registry import (
    list_supported_languages,
    is_language_supported,
    get_language_info,
    RegistryError,
    get_generator_class,
    create_generator,
    is_supported,
    register,
    unregister,
)

from json_explorer.codegen.languages.go import GoGenerator
from json_explorer.codegen.languages.python import PythonGenerator


class TestRegistry:
    """Test generator registry functions."""

    def test_list_supported_languages(self):
        languages = list_supported_languages()

        assert isinstance(languages, list)
        assert len(languages) > 0
        assert "go" in languages
        assert "python" in languages

    def test_is_language_supported(self):
        assert is_language_supported("go") is True
        assert is_language_supported("python") is True
        assert is_language_supported("golang") is True  # alias
        assert is_language_supported("py") is True  # alias
        assert is_language_supported("nonexistent") is False

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
                return Path(".")

            def generate(self, schemas, root_schema_name):
                return "mock code"

        register("mock", MockGenerator, aliases=["test"])

        assert is_supported("mock")
        assert is_supported("test")

        # Cleanup
        unregister("mock")
