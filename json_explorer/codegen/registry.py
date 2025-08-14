"""
Generator registry system for managing available code generators.

Provides dynamic registration and instantiation of language generators.
"""

from typing import Dict, Type, Optional, Any, List
from .core.generator import CodeGenerator
from .core.config import load_config


class GeneratorRegistry:
    """Registry for managing available code generators."""

    def __init__(self):
        """Initialize empty registry."""
        self._generators: Dict[str, Type[CodeGenerator]] = {}
        self._aliases: Dict[str, str] = {}

    def register(
        self,
        language: str,
        generator_class: Type[CodeGenerator],
        aliases: Optional[List[str]] = None,
    ):
        """
        Register a generator for a language.

        Args:
            language: Primary language name (e.g., 'go', 'python')
            generator_class: Generator class implementing CodeGenerator
            aliases: Alternative names for this language
        """
        if not issubclass(generator_class, CodeGenerator):
            raise ValueError(f"Generator class must inherit from CodeGenerator")

        self._generators[language.lower()] = generator_class

        # Register aliases
        if aliases:
            for alias in aliases:
                self._aliases[alias.lower()] = language.lower()

    def unregister(self, language: str):
        """Unregister a generator."""
        language = language.lower()
        if language in self._generators:
            del self._generators[language]

        # Remove aliases pointing to this language
        aliases_to_remove = [
            alias for alias, target in self._aliases.items() if target == language
        ]
        for alias in aliases_to_remove:
            del self._aliases[alias]

    def get_generator_class(self, language: str) -> Type[CodeGenerator]:
        """Get generator class for language."""
        language = language.lower()

        # Check direct registration
        if language in self._generators:
            return self._generators[language]

        # Check aliases
        if language in self._aliases:
            target_language = self._aliases[language]
            return self._generators[target_language]

        raise KeyError(f"No generator registered for language: {language}")

    def create_generator(
        self, language: str, config: Optional[Dict[str, Any]] = None
    ) -> CodeGenerator:
        """
        Create generator instance for language.

        Args:
            language: Language name
            config: Configuration dict or file path

        Returns:
            Configured generator instance
        """
        generator_class = self.get_generator_class(language)

        # Load configuration if needed
        if isinstance(config, str):
            # Config is a file path
            final_config = load_config(language, config_file=config)
            config_dict = {
                "package_name": final_config.package_name,
                "use_pointers_for_optional": final_config.use_pointers_for_optional,
                "generate_json_tags": final_config.generate_json_tags,
                "json_tag_omitempty": final_config.json_tag_omitempty,
                "struct_case": final_config.struct_case,
                "field_case": final_config.field_case,
                "add_comments": final_config.add_comments,
                **final_config.custom,
            }
        else:
            config_dict = config or {}

        return generator_class(config_dict)

    def list_languages(self) -> List[str]:
        """Get list of registered languages."""
        return sorted(self._generators.keys())

    def list_all_names(self) -> Dict[str, List[str]]:
        """Get all registered names including aliases."""
        result = {}
        for language in self._generators:
            names = [language]
            aliases = [
                alias for alias, target in self._aliases.items() if target == language
            ]
            names.extend(aliases)
            result[language] = sorted(names)
        return result

    def is_supported(self, language: str) -> bool:
        """Check if language is supported."""
        language = language.lower()
        return language in self._generators or language in self._aliases


# Global registry instance
_global_registry = GeneratorRegistry()


def get_registry() -> GeneratorRegistry:
    """Get the global generator registry."""
    return _global_registry


def register_generator(
    language: str,
    generator_class: Type[CodeGenerator],
    aliases: Optional[List[str]] = None,
):
    """Register a generator in the global registry."""
    _global_registry.register(language, generator_class, aliases)


def get_generator(
    language: str, config: Optional[Dict[str, Any]] = None
) -> CodeGenerator:
    """Get generator instance from global registry."""
    return _global_registry.create_generator(language, config)


def list_supported_languages() -> List[str]:
    """List all supported languages from global registry."""
    return _global_registry.list_languages()


def is_language_supported(language: str) -> bool:
    """Check if language is supported by global registry."""
    return _global_registry.is_supported(language)


# Auto-discovery functions
def discover_generators():
    """
    Auto-discover and register available generators.

    Looks for generator modules in the languages/ directory.
    """
    import os
    import importlib
    from pathlib import Path

    # Get the languages directory
    languages_dir = Path(__file__).parent / "languages"

    if not languages_dir.exists():
        return

    # Scan for language directories
    for lang_dir in languages_dir.iterdir():
        if not lang_dir.is_dir() or lang_dir.name.startswith("_"):
            continue

        try:
            # Try to import the generator module
            module_name = f"json_explorer.codegen.languages.{lang_dir.name}.generator"
            module = importlib.import_module(module_name)

            # Look for a generator class
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if (
                    isinstance(attr, type)
                    and issubclass(attr, CodeGenerator)
                    and attr != CodeGenerator
                ):

                    # Register the generator
                    _global_registry.register(lang_dir.name, attr)
                    break

        except ImportError:
            # Skip languages that can't be imported
            continue


# Initialize with auto-discovery
try:
    discover_generators()
except Exception:
    # Don't fail if auto-discovery fails
    pass
