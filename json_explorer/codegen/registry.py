"""
Generator registry system.

Manages available code generators and provides lookup by language name.
Uses a simple dict-based approach instead of complex singleton pattern.
"""

from pathlib import Path
from typing import Any

from json_explorer.errors import JsonExplorerError
from json_explorer.logging_config import get_logger

from .core.config import GeneratorConfig, load_config
from .core.generator import CodeGenerator

logger = get_logger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class RegistryError(JsonExplorerError):
    """Raised for registry-related errors."""


# ============================================================================
# Generator Registry (Module-Level)
# ============================================================================


# Generator registry: language name -> generator class
_GENERATORS: dict[str, type[CodeGenerator]] = {}

# Language aliases: alias -> primary language name
_ALIASES: dict[str, str] = {}

# Track if auto-registration has run
_AUTO_REGISTERED = False


def _auto_register_generators() -> None:
    """
    Auto-register known generators with their aliases.

    This runs once on first registry access to discover and register
    all available language generators.
    """
    global _AUTO_REGISTERED

    if _AUTO_REGISTERED:
        return

    logger.info("Auto-registering available generators...")
    registered_count = 0

    # Register Go generator
    try:
        from .languages.go import GoGenerator

        register("go", GoGenerator, aliases=["golang"])
        registered_count += 1
        logger.debug("Registered Go generator")
    except ImportError as e:
        logger.debug("Go generator not available: %s", e)

    # Register Python generator
    try:
        from .languages.python import PythonGenerator

        register("python", PythonGenerator, aliases=["py"])
        registered_count += 1
        logger.debug("Registered Python generator")
    except ImportError as e:
        logger.debug("Python generator not available: %s", e)

    # Future generators can be added here:
    # try:
    #     from .languages.typescript import TypeScriptGenerator
    #     register("typescript", TypeScriptGenerator, aliases=["ts"])
    # except ImportError:
    #     pass

    _AUTO_REGISTERED = True
    logger.info("Auto-registration complete: %s generators available", registered_count)


def _ensure_registry_initialized() -> None:
    """Ensure auto-registration has run."""
    if not _AUTO_REGISTERED:
        _auto_register_generators()


# ============================================================================
# Registration Functions
# ============================================================================


def register(
    language: str,
    generator_class: type[CodeGenerator],
    aliases: list[str] | None = None,
    replace: bool = False,
) -> None:
    """
    Register a generator for a language.

    Args:
        language: Primary language name (e.g., 'go', 'python')
        generator_class: Generator class (subclass of CodeGenerator)
        aliases: Alternative names for this language
        replace: If True, replace existing; if False, skip if exists

    Raises:
        RegistryError: If generator_class is invalid or alias conflicts
    """
    if not issubclass(generator_class, CodeGenerator):
        raise RegistryError(
            f"{generator_class.__name__} must inherit from CodeGenerator"
        )

    language_key = language.lower()

    # Check if already registered
    if language_key in _GENERATORS and not replace:
        logger.debug("Generator already registered for '%s', skipping", language)
        return

    # Register primary name
    _GENERATORS[language_key] = generator_class
    logger.info("Registered generator: %s → %s", language, generator_class.__name__)

    # Register aliases
    if aliases:
        for alias in aliases:
            alias_key = alias.lower()

            if alias_key == language_key:
                continue  # Skip if alias is same as primary

            if not replace:
                # Check for conflicts
                if alias_key in _GENERATORS:
                    raise RegistryError(
                        f"Alias '{alias}' conflicts with existing primary language"
                    )
                if alias_key in _ALIASES and _ALIASES[alias_key] != language_key:
                    raise RegistryError(
                        f"Alias '{alias}' already points to '{_ALIASES[alias_key]}'"
                    )

            _ALIASES[alias_key] = language_key
            logger.debug("Registered alias: %s → %s", alias, language)


# ============================================================================
# Lookup Functions
# ============================================================================


def get_generator_class(language: str) -> type[CodeGenerator]:
    """
    Get generator class for language.

    Args:
        language: Language name or alias

    Returns:
        Generator class

    Raises:
        RegistryError: If language not found
    """
    _ensure_registry_initialized()

    language_key = language.lower()

    # Check direct registration
    if language_key in _GENERATORS:
        return _GENERATORS[language_key]

    # Check aliases
    if language_key in _ALIASES:
        target = _ALIASES[language_key]
        return _GENERATORS[target]

    # Not found
    available = list_languages()
    raise RegistryError(
        f"No generator for language: {language}. Available: {', '.join(available)}"
    )


def create_generator(
    language: str,
    config: GeneratorConfig | dict[str, Any] | str | Path | None = None,
) -> CodeGenerator:
    """
    Create generator instance for language.

    Args:
        language: Language name or alias
        config: Configuration (GeneratorConfig, dict, file path, or None)

    Returns:
        Configured generator instance

    Raises:
        RegistryError: If generator creation fails
    """
    try:
        # Get generator class
        generator_class = get_generator_class(language)

        # Load/convert config
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

        # Create generator
        generator = generator_class(final_config)
        logger.info("Created %s generator", language)
        return generator

    except Exception as e:
        raise RegistryError(f"Failed to create {language} generator: {e}") from e


# ============================================================================
# Query Functions
# ============================================================================


def list_languages() -> list[str]:
    """
    Get list of registered primary language names.

    Returns:
        Sorted list of language names
    """
    _ensure_registry_initialized()
    return sorted(_GENERATORS.keys())


def is_supported(language: str) -> bool:
    """
    Check if language is supported.

    Args:
        language: Language name or alias

    Returns:
        True if supported (either primary or alias)
    """
    _ensure_registry_initialized()
    language_key = language.lower()
    return language_key in _GENERATORS or language_key in _ALIASES


def get_aliases(language: str) -> list[str]:
    """
    Get all aliases for a specific language.

    Args:
        language: Primary language name

    Returns:
        Sorted list of aliases
    """
    _ensure_registry_initialized()
    language_key = language.lower()

    return sorted(
        [alias for alias, target in _ALIASES.items() if target == language_key]
    )


def get_language_info(language: str) -> dict[str, Any]:
    """
    Get information about a registered language.

    Args:
        language: Language name or alias

    Returns:
        Dictionary with language information

    Raises:
        RegistryError: If language not found
    """
    generator_class = get_generator_class(language)

    # Resolve to primary name if alias was provided
    language_key = language.lower()
    if language_key in _ALIASES:
        language_key = _ALIASES[language_key]

    # Create temporary instance to get info
    temp_config = load_config()
    temp_generator = generator_class(temp_config)

    return {
        "name": temp_generator.language_name,
        "class": generator_class.__name__,
        "file_extension": temp_generator.file_extension,
        "aliases": get_aliases(language_key),
        "module": generator_class.__module__,
    }


def list_all_language_info() -> dict[str, dict[str, Any]]:
    """
    Get information about all registered languages.

    Returns:
        Dictionary mapping language name to info dict
    """
    _ensure_registry_initialized()

    result = {}
    for language in list_languages():
        try:
            result[language] = get_language_info(language)
        except Exception as e:
            logger.warning("Failed to get info for %s: %s", language, e)
            continue

    return result
