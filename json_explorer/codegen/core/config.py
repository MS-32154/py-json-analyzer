"""
Configuration management for code generation.

Handles loading, validation, and merging of configuration from multiple sources:
- Default values
- JSON config files
- Programmatic overrides
"""

import json
from dataclasses import dataclass, field, asdict
from pathlib import Path
from typing import Any

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


class ConfigError(Exception):
    """Raised when configuration is invalid or cannot be loaded."""

    pass


# ============================================================================
# Main Configuration Dataclass
# ============================================================================


@dataclass(slots=True, kw_only=True)
class GeneratorConfig:
    """
    Configuration for code generators.

    Attributes:
        package_name: Package/namespace name for generated code
        indent_size: Number of spaces per indent level
        use_tabs: Use tabs instead of spaces
        line_ending: Line ending style (\\n or \\r\\n)
        struct_case: Case style for struct/class names
        field_case: Case style for field names
        generate_json_tags: Whether to generate JSON tags/annotations
        json_tag_omitempty: Add omitempty to JSON tags
        json_tag_case: Case style for JSON tag names
        add_comments: Include comments/documentation in output
        language_config: Language-specific configuration options
    """

    # Output settings
    package_name: str = "main"

    # Code style
    indent_size: int = 4
    use_tabs: bool = False
    line_ending: str = "\n"

    # Naming conventions
    struct_case: str = "pascal"  # pascal, camel, snake
    field_case: str = "pascal"  # pascal, camel, snake

    # JSON serialization
    generate_json_tags: bool = True
    json_tag_omitempty: bool = True
    json_tag_case: str = "original"  # original, snake, camel

    # Documentation
    add_comments: bool = True

    # Language-specific settings (extensible)
    language_config: dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        """Validate configuration after initialization."""
        self._validate()

    def _validate(self) -> None:
        """Validate configuration values."""
        if self.indent_size < 1:
            raise ConfigError("indent_size must be at least 1")

        if self.struct_case not in {"pascal", "camel", "snake"}:
            raise ConfigError(
                f"struct_case must be pascal, camel, or snake (got: {self.struct_case})"
            )

        if self.field_case not in {"pascal", "camel", "snake"}:
            raise ConfigError(
                f"field_case must be pascal, camel, or snake (got: {self.field_case})"
            )

        if self.json_tag_case not in {"original", "snake", "camel"}:
            raise ConfigError(
                f"json_tag_case must be original, snake, or camel (got: {self.json_tag_case})"
            )

        logger.debug(
            f"Config validated: package={self.package_name}, comments={self.add_comments}"
        )

    def merge(self, overrides: dict[str, Any]) -> "GeneratorConfig":
        """
        Create new config by merging with overrides.

        Args:
            overrides: Dictionary of values to override

        Returns:
            New GeneratorConfig instance with merged values
        """
        current = asdict(self)

        # Separate known fields from language_config
        known_fields = {
            "package_name",
            "indent_size",
            "use_tabs",
            "line_ending",
            "struct_case",
            "field_case",
            "generate_json_tags",
            "json_tag_omitempty",
            "json_tag_case",
            "add_comments",
            "language_config",
        }

        config_updates = {}
        lang_config_updates = {}

        for key, value in overrides.items():
            if key in known_fields:
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

        logger.debug(f"Config merged with {len(overrides)} overrides")
        return GeneratorConfig(**current)

    def to_dict(self) -> dict[str, Any]:
        """Convert config to dictionary."""
        return asdict(self)

    def to_json(self, indent: int = 2) -> str:
        """Convert config to JSON string."""
        return json.dumps(self.to_dict(), indent=indent)


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
        with open(config_path, encoding="utf-8") as f:
            config_data = json.load(f)

        if not isinstance(config_data, dict):
            raise ConfigError(
                f"Configuration file must contain JSON object: {config_path}"
            )

        logger.info(f"Loaded config from: {config_path}")
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

        with open(path, "w", encoding="utf-8") as f:
            json.dump(config.to_dict(), f, indent=2, ensure_ascii=False)

        logger.info(f"Saved config to: {path}")

    except OSError as e:
        raise ConfigError(f"Failed to save configuration to {path}: {e}") from e


# ============================================================================
# Preset Configurations
# ============================================================================


def create_minimal_config() -> GeneratorConfig:
    """
    Create minimal configuration (no comments, basic settings).

    Useful for generating compact code without documentation.
    """
    return GeneratorConfig(
        add_comments=False,
        generate_json_tags=True,
        json_tag_omitempty=False,
    )


def create_verbose_config() -> GeneratorConfig:
    """
    Create verbose configuration with all documentation.

    Useful for learning or when documentation is critical.
    """
    return GeneratorConfig(
        add_comments=True,
        generate_json_tags=True,
        json_tag_omitempty=True,
    )


def create_strict_config() -> GeneratorConfig:
    """
    Create strict configuration (no optional handling).

    Useful for schemas where all fields are required.
    """
    return GeneratorConfig(
        json_tag_omitempty=False,
        language_config={"use_pointers_for_optional": False},
    )


# ============================================================================
# Configuration Validation Helpers
# ============================================================================


def validate_language_config(
    config: GeneratorConfig,
    required_keys: set[str] | None = None,
    optional_keys: set[str] | None = None,
) -> list[str]:
    """
    Validate language-specific configuration.

    Args:
        config: Configuration to validate
        required_keys: Keys that must be present in language_config
        optional_keys: Keys that are allowed but not required

    Returns:
        List of warning messages (empty if valid)
    """
    warnings = []
    required = required_keys or set()
    optional = optional_keys or set()

    lang_config = config.language_config

    # Check required keys
    missing = required - lang_config.keys()
    if missing:
        warnings.append(f"Missing required language config: {', '.join(missing)}")

    # Check for unknown keys
    if optional:
        known = required | optional
        unknown = lang_config.keys() - known
        if unknown:
            warnings.append(f"Unknown language config keys: {', '.join(unknown)}")

    return warnings
