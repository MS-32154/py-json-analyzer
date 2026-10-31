"""
Tests for generator registry.
"""

from pathlib import Path

import pytest
from json_explorer.codegen.core import (
    CodeGenerator,
    GeneratorConfig,
)
from json_explorer.codegen.core.plugin import CliOption, LanguagePlugin
from json_explorer.codegen.languages.go import GoGenerator
from json_explorer.codegen.languages.python import PythonGenerator
from json_explorer.codegen.registry import (
    _ALIASES,
    _PLUGINS,
    RegistryError,
    all_plugins,
    create_generator,
    get_generator_class,
    get_language_info,
    get_plugin,
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
            language_name = "mock"
            file_extension = ".mock"
            template_dir = Path()

            def generate(self, schemas, root_schema_name):
                return "mock code"

        register(
            LanguagePlugin(name="mock", generator=MockGenerator, aliases=("test",))
        )
        try:
            assert is_supported("mock")
            assert is_supported("test")
            assert get_plugin("TEST").generator is MockGenerator
            assert get_language_info("mock")["file_extension"] == ".mock"
        finally:
            del _PLUGINS["mock"]
            del _ALIASES["test"]

    def test_duplicate_registration_rejected(self):
        with pytest.raises(RegistryError):
            register(get_plugin("go"))

    def test_alias_conflict_rejected(self):
        plugin = LanguagePlugin(
            name="other", generator=get_plugin("go").generator, aliases=("py",)
        )
        with pytest.raises(RegistryError):
            register(plugin)
        assert "other" not in _PLUGINS


class TestLanguagePlugins:
    """Each plugin owns its CLI flags; the CLI maps them to config options."""

    def test_builtin_plugins(self):
        assert [p.name for p in all_plugins()] == ["go", "python", "rust", "typescript"]

    def test_flags_map_to_config(self):
        import argparse

        plugin = LanguagePlugin(
            name="demo",
            generator=get_plugin("go").generator,
            cli_options=(
                CliOption("--no-thing", "thing", "help", value=False),
                CliOption("--style", "style", "help", choices=("a", "b")),
            ),
        )
        parser = argparse.ArgumentParser()
        plugin.add_cli_arguments(parser)
        assert plugin.config_from_args(parser.parse_args([])) == {}
        args = parser.parse_args(["--no-thing", "--style", "b"])
        assert plugin.config_from_args(args) == {"thing": False, "style": "b"}

    def test_every_flag_targets_a_real_option(self):
        """A flag must set an option the language's generator accepts."""
        for plugin in all_plugins():
            for opt in plugin.cli_options:
                value = opt.choices[0] if opt.choices else opt.value
                if opt.option not in GeneratorConfig.__dataclass_fields__:
                    create_generator(plugin.name, {opt.option: value})


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
