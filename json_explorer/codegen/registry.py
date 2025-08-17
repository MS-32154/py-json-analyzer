"""
Generator registry system for managing available code generators.

Provides dynamic registration and instantiation of language generators.
"""

from typing import Dict, Type, Optional, Any, List, Union
from pathlib import Path
from .core.generator import CodeGenerator
from .core.config import GeneratorConfig, load_config


class RegistryError(Exception):
    """Exception raised for registry-related errors."""

    pass


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

        Raises:
            RegistryError: If generator class is invalid
        """
        if not issubclass(generator_class, CodeGenerator):
            raise RegistryError(f"Generator class must inherit from CodeGenerator")

        language_key = language.lower()
        self._generators[language_key] = generator_class

        # Register aliases
        if aliases:
            for alias in aliases:
                alias_key = alias.lower()
                if alias_key in self._generators or alias_key in self._aliases:
                    raise RegistryError(f"Alias '{alias}' already registered")
                self._aliases[alias_key] = language_key

    def unregister(self, language: str):
        """
        Unregister a generator and its aliases.

        Args:
            language: Language name to unregister
        """
        language_key = language.lower()

        if language_key in self._generators:
            del self._generators[language_key]

        # Remove aliases pointing to this language
        aliases_to_remove = [
            alias for alias, target in self._aliases.items() if target == language_key
        ]
        for alias in aliases_to_remove:
            del self._aliases[alias]

    def get_generator_class(self, language: str) -> Type[CodeGenerator]:
        """
        Get generator class for language.

        Args:
            language: Language name or alias

        Returns:
            Generator class

        Raises:
            RegistryError: If language not found
        """
        language_key = language.lower()

        # Check direct registration
        if language_key in self._generators:
            return self._generators[language_key]

        # Check aliases
        if language_key in self._aliases:
            target_language = self._aliases[language_key]
            return self._generators[target_language]

        available = self.list_all_names()
        raise RegistryError(
            f"No generator registered for language: {language}. "
            f"Available: {list(available.keys())}"
        )

    def create_generator(
        self,
        language: str,
        config: Optional[Union[GeneratorConfig, Dict[str, Any], str, Path]] = None,
    ) -> CodeGenerator:
        """
        Create generator instance for language.

        Args:
            language: Language name
            config: Configuration as GeneratorConfig, dict, or file path

        Returns:
            Configured generator instance

        Raises:
            RegistryError: If generator creation fails
        """
        try:
            generator_class = self.get_generator_class(language)

            # Handle different config types
            if isinstance(config, GeneratorConfig):
                final_config = config
            elif isinstance(config, (str, Path)):
                # Config is a file path
                final_config = load_config(config_file=config)
            elif isinstance(config, dict):
                # Config is a dictionary
                final_config = load_config(custom_config=config)
            elif config is None:
                # Use defaults
                final_config = load_config()
            else:
                raise RegistryError(f"Invalid config type: {type(config)}")

            return generator_class(final_config)

        except Exception as e:
            raise RegistryError(f"Failed to create {language} generator: {e}")

    def list_languages(self) -> List[str]:
        """Get list of registered primary language names."""
        return sorted(self._generators.keys())

    def list_all_names(self) -> Dict[str, List[str]]:
        """
        Get all registered names including aliases.

        Returns:
            Dict mapping primary language to list of all names (including aliases)
        """
        result = {}
        for language in self._generators:
            names = [language]
            aliases = [
                alias for alias, target in self._aliases.items() if target == language
            ]
            names.extend(sorted(aliases))
            result[language] = names
        return result

    def is_supported(self, language: str) -> bool:
        """
        Check if language is supported.

        Args:
            language: Language name or alias

        Returns:
            True if supported
        """
        language_key = language.lower()
        return language_key in self._generators or language_key in self._aliases

    def get_language_info(self, language: str) -> Dict[str, Any]:
        """
        Get information about a registered language.

        Args:
            language: Language name

        Returns:
            Dict with language information

        Raises:
            RegistryError: If language not found
        """
        generator_class = self.get_generator_class(language)

        # Create temporary instance to get info
        temp_config = load_config()
        temp_generator = generator_class(temp_config)

        language_key = language.lower()
        aliases = [
            alias for alias, target in self._aliases.items() if target == language_key
        ]

        return {
            "name": temp_generator.language_name,
            "class": generator_class.__name__,
            "file_extension": temp_generator.file_extension,
            "aliases": aliases,
            "module": generator_class.__module__,
        }


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
    """
    Register a generator in the global registry.

    Args:
        language: Language name
        generator_class: Generator class
        aliases: Optional aliases
    """
    _global_registry.register(language, generator_class, aliases)


def get_generator(
    language: str,
    config: Optional[Union[GeneratorConfig, Dict[str, Any], str, Path]] = None,
) -> CodeGenerator:
    """
    Get generator instance from global registry.

    Args:
        language: Language name
        config: Configuration

    Returns:
        Generator instance
    """
    return _global_registry.create_generator(language, config)


def list_supported_languages() -> List[str]:
    """List all supported languages from global registry."""
    return _global_registry.list_languages()


def is_language_supported(language: str) -> bool:
    """Check if language is supported by global registry."""
    return _global_registry.is_supported(language)


def get_language_info(language: str) -> Dict[str, Any]:
    """Get information about a supported language."""
    return _global_registry.get_language_info(language)


def list_all_language_info() -> Dict[str, Dict[str, Any]]:
    """Get information about all supported languages."""
    result = {}
    for language in list_supported_languages():
        try:
            result[language] = get_language_info(language)
        except Exception:
            # Skip languages that can't provide info
            continue
    return result


# Auto-discovery functions
def discover_generators():
    """
    Auto-discover and register available generators.

    Looks for generator modules in the languages/ directory.
    """
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
            # Try to import the language module
            module_name = f".languages.{lang_dir.name}"
            module = importlib.import_module(module_name, package=__package__)

            # Look for generator classes in the module's __all__ or by inspection
            generator_classes = []

            if hasattr(module, "__all__"):
                # Check items in __all__
                for name in module.__all__:
                    if name.endswith("Generator"):
                        attr = getattr(module, name, None)
                        if (
                            isinstance(attr, type)
                            and issubclass(attr, CodeGenerator)
                            and attr != CodeGenerator
                        ):
                            generator_classes.append(attr)
            else:
                # Scan module attributes
                for attr_name in dir(module):
                    if not attr_name.endswith("Generator"):
                        continue
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, CodeGenerator)
                        and attr != CodeGenerator
                    ):
                        generator_classes.append(attr)

            # Register found generators
            for generator_class in generator_classes:
                if not _global_registry.is_supported(lang_dir.name):
                    _global_registry.register(lang_dir.name, generator_class)

        except ImportError as e:
            # Skip languages that can't be imported
            continue
        except Exception as e:
            # Skip languages with other issues
            continue


# Initialize with auto-discovery
try:
    discover_generators()
except Exception:
    # Don't fail if auto-discovery fails
    pass
