"""
Tests for core configuration.
"""

import json
import tempfile
from pathlib import Path

import pytest
from json_explorer.codegen.core.config import (
    ConfigError,
    GeneratorConfig,
    load_config,
    save_config,
)


class TestGeneratorConfig:
    """Test GeneratorConfig dataclass."""

    def test_default_config(self):
        config = GeneratorConfig()
        assert config.package_name == "main"
        assert config.add_comments is True

    def test_custom_config(self):
        config = GeneratorConfig(
            package_name="models",
            add_comments=False,
        )
        assert config.package_name == "models"
        assert config.add_comments is False

    def test_config_language_specific(self):
        config = GeneratorConfig(language_config={"custom_option": "value"})
        assert config.language_config["custom_option"] == "value"

    def test_removed_options_are_ignored(self):
        """Old config files with options removed in 0.5.0 still load."""
        merged = GeneratorConfig().merge(
            {"field_case": "camel", "indent_size": 2, "package_name": "models"}
        )
        assert merged.package_name == "models"
        assert "field_case" not in merged.language_config
        assert "indent_size" not in merged.language_config

    def test_merge_config(self):
        config = GeneratorConfig(package_name="main")
        merged = config.merge({"package_name": "models", "add_comments": False})

        assert merged.package_name == "models"
        assert merged.add_comments is False

    def test_to_dict(self):
        config = GeneratorConfig(package_name="test")
        result = config.to_dict()

        assert isinstance(result, dict)
        assert result["package_name"] == "test"


class TestConfigLoading:
    """Test configuration loading."""

    def test_load_from_dict(self):
        config = load_config(custom_config={"package_name": "test"})
        assert config.package_name == "test"

    def test_load_from_file(self):
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump({"package_name": "file_test"}, f)
            temp_path = f.name

        try:
            config = load_config(config_file=temp_path)
            assert config.package_name == "file_test"
        finally:
            Path(temp_path).unlink()

    def test_load_invalid_file(self):
        with pytest.raises(ConfigError):
            load_config(config_file="nonexistent.json")

    def test_save_config(self):
        config = GeneratorConfig(package_name="save_test")

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            temp_path = f.name

        try:
            save_config(config, temp_path)
            loaded = load_config(config_file=temp_path)
            assert loaded.package_name == "save_test"
        finally:
            Path(temp_path).unlink()


class TestLanguageOptionValidation:
    """#14: bad language options fail with a clear ConfigError."""

    @pytest.mark.parametrize(
        ("language", "options", "message"),
        [
            ("go", {"style": "pydantic"}, "Unknown go option(s): style"),
            ("python", {"pakage_name": "x"}, "Valid python options:"),
            ("go", {"int_type": "int8"}, "choose one of: int, int32, int64"),
            (
                "python",
                {"style": "attrs"},
                "choose one of: dataclass, pydantic, typeddict",
            ),
            ("python", {"dataclass_frozen": "yes"}, "must be true or false"),
        ],
    )
    def test_rejected(self, language, options, message):
        from json_explorer.codegen import create_generator

        with pytest.raises(
            ConfigError, match=message.replace("(", r"\(").replace(")", r"\)")
        ):
            create_generator(language, options)

    def test_valid_options_accepted(self):
        from json_explorer.codegen import create_generator

        assert create_generator("go", {"int_type": "int"}).go_config.int_type == "int"
