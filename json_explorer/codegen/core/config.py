"""
Configuration management for code generation.

Handles loading, validation, and merging of configuration from multiple sources:
- Default values
- JSON config files
- Programmatic overrides
"""

import json
import typing
from dataclasses import asdict, dataclass, field, fields
from enum import Enum
from pathlib import Path
from typing import Any

from json_explorer.errors import JsonExplorerError
from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# Options removed in 0.5.0, ignored with a warning so old config files still load.
REMOVED_OPTIONS: dict[str, str] = {
    "struct_case": "type names always follow the target language (PascalCase)",
    "field_case": "field names always follow the target language",
    "json_tag_case": "JSON tags must match the JSON keys exactly",
    "indent_size": "was never applied",
    "use_tabs": "was never applied",
    "line_ending": "was never applied",
    "generate_json_tags": "Go structs without tags mis-map keys; tags are always generated",
    "string_type": "JSON strings are always string/str",
    "bool_type": "JSON booleans are always bool",
    "unknown_type": "unknown values are always any (Go) / Any (Python)",
    "use_optional": "optional fields are always typed as optional",
    "pydantic_use_field": "Field() is used whenever a field needs an alias or default",
    "pydantic_use_alias": "aliases are always generated for renamed fields",
    "typeddict_total": "required keys are required; optional keys use NotRequired",
    "datetime_type": "timestamps are datetime in Pydantic models, str otherwise",
}


class ConfigError(JsonExplorerError):
    """Raised when configuration is invalid or cannot be loaded."""


# ============================================================================
# Main Configuration Dataclass
# ============================================================================


@dataclass(slots=True, kw_only=True)
class GeneratorConfig:
    """
    Configuration for code generators.

    Attributes:
        package_name: Package/namespace name for generated code
        json_tag_omitempty: Add omitempty to JSON tags
        add_comments: Include comments/documentation in output
        language_config: Language-specific configuration options
    """

    # Output settings
    package_name: str = "main"

    # JSON serialization
    json_tag_omitempty: bool = True

    # Documentation
    add_comments: bool = True

    # Language-specific settings (extensible)
    language_config: dict[str, Any] = field(default_factory=dict)

    def merge(self, overrides: dict[str, Any]) -> GeneratorConfig:
        """
        Create new config by merging with overrides.

        Args:
            overrides: Dictionary of values to override

        Returns:
            New GeneratorConfig instance with merged values
        """
        current = asdict(self)

        # Separate known fields from language_config
        known_fields = {f.name for f in fields(self)}

        config_updates = {}
        lang_config_updates = {}

        for key, value in overrides.items():
            if key in REMOVED_OPTIONS:
                logger.warning(
                    "Ignoring removed option %r: %s", key, REMOVED_OPTIONS[key]
                )
            elif key in known_fields:
                config_updates[key] = value
            else:
                # Unknown fields go to language_config
                lang_config_updates[key] = value

        # Merge language_config
        if lang_config_updates:
            merged_lang_config = {**current["language_config"], **lang_config_updates}
            config_updates["language_config"] = merged_lang_config

        # Apply all updates
        current.update(config_updates)

        logger.debug("Config merged with %s overrides", len(overrides))
        return GeneratorConfig(**current)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)


# ============================================================================
# Language option validation
# ============================================================================


def build_language_config[T](cls: type[T], options: dict[str, Any], language: str) -> T:
    """Create a language's option dataclass from ``options``, with clear errors.

    Rejects unknown option names (listing the valid ones) and values outside a
    ``Literal``/``Enum`` choice or of the wrong basic type.
    """
    language_fields = [f for f in fields(cls) if f.init]  # type: ignore[arg-type]
    valid = sorted(f.name for f in language_fields)
    unknown = sorted(set(options) - set(valid))
    if unknown:
        common = sorted(
            f.name for f in fields(GeneratorConfig) if f.name != "language_config"
        )
        raise ConfigError(
            f"Unknown {language} option(s): {', '.join(unknown)}. "
            f"Valid {language} options: {', '.join(valid)}; "
            f"common options: {', '.join(common)}"
        )
    hints = typing.get_type_hints(cls)
    for f in language_fields:
        if f.name not in options:
            continue
        value, hint = options[f.name], hints[f.name]
        if typing.get_origin(hint) is typing.Literal:
            choices = typing.get_args(hint)
        elif isinstance(hint, type) and issubclass(hint, Enum):
            choices = tuple(m.value for m in hint)
            value = value.value if isinstance(value, hint) else value
        elif hint is bool:
            if not isinstance(value, bool):
                raise ConfigError(
                    f"{language} option {f.name} must be true or false, got {value!r}"
                )
            continue
        else:
            continue
        if value not in choices:
            raise ConfigError(
                f"Invalid value {value!r} for {language} option {f.name}; "
                f"choose one of: {', '.join(map(str, choices))}"
            )
    return cls(**options)


# ============================================================================
# Configuration Loading
# ============================================================================


def load_config_file(path: str | Path) -> dict[str, Any]:
    """
    Load configuration from JSON file.

    Args:
        path: Path to JSON configuration file

    Returns:
        Dictionary of configuration values

    Raises:
        ConfigError: If file cannot be loaded or parsed
    """
    config_path = Path(path)

    if not config_path.exists():
        raise ConfigError(f"Configuration file not found: {config_path}")

    if config_path.suffix.lower() != ".json":
        raise ConfigError(f"Configuration file must be JSON: {config_path}")

    try:
        with config_path.open(encoding="utf-8") as f:
            config_data = json.load(f)

        if not isinstance(config_data, dict):
            raise ConfigError(
                f"Configuration file must contain JSON object: {config_path}"
            )

        logger.info("Loaded config from: %s", config_path)
        return config_data

    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in {config_path}: {e}") from e
    except OSError as e:
        raise ConfigError(f"Failed to read {config_path}: {e}") from e


def load_config(
    config_file: str | Path | None = None,
    custom_config: dict[str, Any] | None = None,
) -> GeneratorConfig:
    """
    Load configuration from multiple sources.

    Priority (highest to lowest):
    1. custom_config (programmatic overrides)
    2. config_file (JSON file)
    3. Defaults (from GeneratorConfig)

    Args:
        config_file: Path to JSON configuration file
        custom_config: Dictionary of configuration overrides

    Returns:
        Merged GeneratorConfig instance

    Raises:
        ConfigError: If configuration is invalid
    """
    # Start with defaults
    base_config = GeneratorConfig()

    # Load from file if provided
    if config_file:
        file_config = load_config_file(config_file)
        base_config = base_config.merge(file_config)

    # Apply custom overrides
    if custom_config:
        base_config = base_config.merge(custom_config)

    return base_config


def save_config(config: GeneratorConfig, output_path: str | Path) -> None:
    """
    Save configuration to JSON file.

    Args:
        config: Configuration to save
        output_path: Path where to save the configuration

    Raises:
        ConfigError: If file cannot be written
    """
    path = Path(output_path)

    try:
        path.parent.mkdir(parents=True, exist_ok=True)

        with path.open("w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info("Saved config to: %s", path)

    except OSError as e:
        raise ConfigError(f"Failed to save configuration to {path}: {e}") from e
