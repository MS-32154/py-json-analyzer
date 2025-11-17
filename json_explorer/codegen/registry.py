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
        self._primary_names: Dict[str, str] = (
            {}
        )  # Maps canonical name back to primary key

    def register(
        self,
        language: str,
        generator_class: Type[CodeGenerator],
        aliases: Optional[List[str]] = None,
        replace: bool = False,
    ):
        """
        Register a generator for a language.

        Args:
            language: Primary language name (e.g., 'go', 'python')
            generator_class: Generator class implementing CodeGenerator
            aliases: Alternative names for this language
            replace: If True, replace existing registration. If False, skip if exists.

        Raises:
            RegistryError: If generator class is invalid or conflicts exist
        """
        if not issubclass(generator_class, CodeGenerator):
            raise RegistryError(f"Generator class must inherit from CodeGenerator")

        language_key = language.lower()

        # Check if already registered
        if language_key in self._generators and not replace:
            # Already registered, skip silently
            return

        # Store the generator
        self._generators[language_key] = generator_class
        self._primary_names[language_key] = language_key

        # Register aliases
        if aliases:
            for alias in aliases:
                alias_key = alias.lower()

                # Skip if alias is the same as primary
                if alias_key == language_key:
                    continue

                # Check for conflicts (unless replacing)
                if not replace:
                    if alias_key in self._generators:
                        raise RegistryError(
                            f"Alias '{alias}' conflicts with existing primary language"
                        )
                    if (
                        alias_key in self._aliases
                        and self._aliases[alias_key] != language_key
                    ):
                        raise RegistryError(
                            f"Alias '{alias}' already points to '{self._aliases[alias_key]}'"
                        )

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
            if language_key in self._primary_names:
                del self._primary_names[language_key]

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

        available = self.list_languages()
        raise RegistryError(
            f"No generator registered for language: {language}. "
            f"Available: {', '.join(available)}"
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
                final_config = load_config(config_file=config)
            elif isinstance(config, dict):
                final_config = load_config(custom_config=config)
            elif config is None:
                final_config = load_config()
            else:
                raise RegistryError(f"Invalid config type: {type(config)}")

            return generator_class(final_config)

        except Exception as e:
            raise RegistryError(f"Failed to create {language} generator: {e}")

    def list_languages(self) -> List[str]:
        """Get list of registered primary language names."""
        return sorted(self._generators.keys())

    def get_aliases_for_language(self, language: str) -> List[str]:
        """
        Get all aliases for a specific language.

        Args:
            language: Primary language name

        Returns:
            List of aliases for this language
        """
        language_key = language.lower()
        return sorted(
            [alias for alias, target in self._aliases.items() if target == language_key]
        )

    def list_all_names(self) -> Dict[str, List[str]]:
        """
        Get all registered names including aliases.

        Returns:
            Dict mapping primary language to list of all names (including aliases)
        """
        result = {}
        for language in self._generators:
            names = [language]
            aliases = self.get_aliases_for_language(language)
            names.extend(aliases)
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

        # Resolve to primary language if an alias was provided
        language_key = language.lower()
        if language_key in self._aliases:
            language_key = self._aliases[language_key]

        # Create temporary instance to get info
        temp_config = load_config()
        temp_generator = generator_class(temp_config)

        aliases = self.get_aliases_for_language(language_key)

        return {
            "name": temp_generator.language_name,
            "class": generator_class.__name__,
            "file_extension": temp_generator.file_extension,
            "aliases": aliases,
            "module": generator_class.__module__,
        }


# Global registry instance - created once
_global_registry: Optional[GeneratorRegistry] = None


def get_registry() -> GeneratorRegistry:
    """Get the global generator registry, initializing if needed."""
    global _global_registry
    if _global_registry is None:
        _global_registry = GeneratorRegistry()
        _auto_register_generators()
    return _global_registry


def _auto_register_generators():
    """
    Auto-register known generators with their aliases.

    This is the single source of truth for generator registration.
    Each language module should export its configuration here.
    """
    # Register Go generator
    try:
        from .languages.go import GoGenerator

        _global_registry.register("go", GoGenerator, aliases=["golang"])
    except ImportError:
        pass

    # Future languages will be added here:
    try:
        from .languages.python import PythonGenerator

        _global_registry.register("python", PythonGenerator, aliases=["py"])
    except ImportError:
        pass


# Public API functions using the global registry


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
    get_registry().register(language, generator_class, aliases)


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
    return get_registry().create_generator(language, config)


def list_supported_languages() -> List[str]:
    """List all supported languages from global registry."""
    return get_registry().list_languages()


def is_language_supported(language: str) -> bool:
    """Check if language is supported by global registry."""
    return get_registry().is_supported(language)


def get_language_info(language: str) -> Dict[str, Any]:
    """Get information about a supported language."""
    return get_registry().get_language_info(language)


def list_all_language_info() -> Dict[str, Dict[str, Any]]:
    """Get information about all supported languages."""
    result = {}
    for language in list_supported_languages():
        try:
            result[language] = get_language_info(language)
        except Exception:
            continue
    return result
