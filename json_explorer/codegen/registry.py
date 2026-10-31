"""Registry of target languages.

Built-in languages and those installed through the ``json_explorer.languages``
entry-point group (each entry point loads a :class:`LanguagePlugin`) are
registered on first use.
"""

from importlib import import_module
from importlib.metadata import entry_points
from pathlib import Path
from typing import Any

from json_explorer.errors import JsonExplorerError
from json_explorer.logging_config import get_logger

from .core.config import GeneratorConfig, load_config
from .core.generator import CodeGenerator
from .core.plugin import LanguagePlugin

logger = get_logger(__name__)

ENTRY_POINT_GROUP = "json_explorer.languages"
_BUILTIN_PLUGINS = (
    "json_explorer.codegen.languages.go",
    "json_explorer.codegen.languages.python",
    "json_explorer.codegen.languages.typescript",
)


class RegistryError(JsonExplorerError):
    """Raised for unknown languages or invalid registrations."""


_PLUGINS: dict[str, LanguagePlugin] = {}
_ALIASES: dict[str, str] = {}
_loaded = False


def _ensure_loaded() -> None:
    global _loaded
    if _loaded:
        return
    _loaded = True
    for module in _BUILTIN_PLUGINS:
        register(import_module(module).PLUGIN)
    for entry_point in entry_points(group=ENTRY_POINT_GROUP):
        try:
            register(entry_point.load())
        except Exception:
            logger.warning(
                "Could not load language plugin %r", entry_point.name, exc_info=True
            )


def register(plugin: LanguagePlugin, *, replace: bool = False) -> None:
    """Register a language plugin (and its aliases)."""
    if not issubclass(plugin.generator, CodeGenerator):
        raise RegistryError(
            f"{plugin.generator.__name__} must inherit from CodeGenerator"
        )
    key = plugin.name.lower()
    if key in _PLUGINS and not replace:
        raise RegistryError(f"Language {plugin.name!r} is already registered")
    for alias in plugin.aliases:
        owner = _ALIASES.get(alias.lower())
        if alias.lower() in _PLUGINS or (owner and owner != key):
            raise RegistryError(f"Alias {alias!r} is already in use")
    _PLUGINS[key] = plugin
    for alias in plugin.aliases:
        _ALIASES[alias.lower()] = key


def get_plugin(language: str) -> LanguagePlugin:
    """Plugin for a language name or alias."""
    _ensure_loaded()
    key = language.lower()
    key = _ALIASES.get(key, key)
    if key not in _PLUGINS:
        raise RegistryError(
            f"No generator for language: {language}. "
            f"Available: {', '.join(list_languages())}"
        )
    return _PLUGINS[key]


def all_plugins() -> list[LanguagePlugin]:
    _ensure_loaded()
    return [_PLUGINS[name] for name in sorted(_PLUGINS)]


def get_generator_class(language: str) -> type[CodeGenerator]:
    return get_plugin(language).generator


def create_generator(
    language: str,
    config: GeneratorConfig | dict[str, Any] | str | Path | None = None,
) -> CodeGenerator:
    """Generator for a language, configured from a GeneratorConfig, an options
    dict, a JSON config file path, or the defaults."""
    generator_class = get_generator_class(language)
    match config:
        case GeneratorConfig():
            final_config = config
        case str() | Path():
            final_config = load_config(config_file=config)
        case dict():
            final_config = load_config(custom_config=config)
        case None:
            final_config = load_config()
        case _:
            raise RegistryError(f"Invalid config type: {type(config).__name__}")
    try:
        return generator_class(final_config)
    except JsonExplorerError:
        raise
    except Exception as e:
        raise RegistryError(f"Failed to create {language} generator: {e}") from e


def list_languages() -> list[str]:
    """Registered language names (without aliases), sorted."""
    _ensure_loaded()
    return sorted(_PLUGINS)


def is_supported(language: str) -> bool:
    _ensure_loaded()
    key = language.lower()
    return key in _PLUGINS or key in _ALIASES


def get_aliases(language: str) -> list[str]:
    return sorted(get_plugin(language).aliases)


def get_language_info(language: str) -> dict[str, Any]:
    plugin = get_plugin(language)
    return {
        "name": plugin.name,
        "class": plugin.generator.__name__,
        "file_extension": plugin.generator.file_extension,
        "aliases": sorted(plugin.aliases),
        "module": plugin.generator.__module__,
    }


def list_all_language_info() -> dict[str, dict[str, Any]]:
    return {plugin.name: get_language_info(plugin.name) for plugin in all_plugins()}
