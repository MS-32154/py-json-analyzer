import pytest
from json_explorer.codegen import quick_generate
from json_explorer.codegen.registry import get_generator_class


class TestErrorHandling:
    """Test error handling."""

    def test_invalid_language(self):
        from json_explorer.codegen.registry import RegistryError

        with pytest.raises(RegistryError):
            get_generator_class("invalid_language")

    def test_invalid_json_data(self):
        from json_explorer.codegen.core.generator import GeneratorError

        with pytest.raises(GeneratorError):
            quick_generate("invalid json string", "go")
