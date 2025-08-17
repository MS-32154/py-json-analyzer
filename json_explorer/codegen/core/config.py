"""
Configuration management for code generation.

Handles loading and merging configuration from JSON files,
providing defaults and validation for generator settings.
"""

import json
from pathlib import Path
from typing import Dict, Any, Optional, Union
from dataclasses import dataclass, field


class ConfigError(Exception):
    """Exception raised for configuration-related errors."""

    pass


@dataclass
class GeneratorConfig:
    """Base configuration for code generators."""

    # Output settings
    output_file: Optional[str] = None
    package_name: str = "main"

    # Code style settings
    indent_size: int = 4
    use_tabs: bool = False
    line_ending: str = "\n"

    # Naming settings
    struct_case: str = "pascal"  # pascal, camel, snake
    field_case: str = "pascal"  # pascal, camel, snake

    # JSON settings
    generate_json_tags: bool = True
    json_tag_omitempty: bool = True
    json_tag_case: str = "original"  # original, snake, camel

    # Additional metadata
    add_comments: bool = True

    # Language-specific settings (extensible)
    language_config: Dict[str, Any] = field(default_factory=dict)


def load_config(
    config_file: Optional[Union[str, Path]] = None,
    custom_config: Optional[Dict[str, Any]] = None,
) -> GeneratorConfig:
    """
    Load configuration from file and/or custom overrides.

    Args:
        config_file: Path to JSON configuration file
        custom_config: Custom configuration overrides

    Returns:
        Merged configuration
    """
    base_config = {}

    # Load from file if provided
    if config_file:
        base_config = _load_config_file(config_file)

    # Apply custom overrides
    if custom_config:
        base_config.update(custom_config)

    # Create GeneratorConfig instance
    return _dict_to_config(base_config)


def _load_config_file(config_path: Union[str, Path]) -> Dict[str, Any]:
    """Load configuration from JSON file."""
    path = Path(config_path)

    if not path.exists():
        raise ConfigError(f"Configuration file not found: {path}")

    if not path.suffix.lower() == ".json":
        raise ConfigError(f"Configuration file must be JSON: {path}")

    try:
        with open(path, "r", encoding="utf-8") as f:
            config = json.load(f)

        if not isinstance(config, dict):
            raise ConfigError(f"Configuration file must contain a JSON object: {path}")

        return config

    except json.JSONDecodeError as e:
        raise ConfigError(f"Invalid JSON in configuration file {path}: {str(e)}")
    except Exception as e:
        raise ConfigError(f"Failed to load configuration file {path}: {str(e)}")


def _dict_to_config(config_dict: Dict[str, Any]) -> GeneratorConfig:
    """Convert dictionary to GeneratorConfig instance."""
    # Extract known fields
    known_fields = {f.name for f in GeneratorConfig.__dataclass_fields__.values()}

    config_args = {}
    language_args = {}

    for key, value in config_dict.items():
        if key in known_fields:
            config_args[key] = value
        else:
            # Unknown fields go to language_config
            language_args[key] = value

    # Add language-specific fields to the language_config dict
    if language_args:
        existing_language = config_args.get("language_config", {})
        existing_language.update(language_args)
        config_args["language_config"] = existing_language

    return GeneratorConfig(**config_args)


def save_config(config: GeneratorConfig, output_path: Union[str, Path]):
    """Save configuration to JSON file."""
    path = Path(output_path)

    # Convert GeneratorConfig to dictionary
    config_dict = {
        "output_file": config.output_file,
        "package_name": config.package_name,
        "indent_size": config.indent_size,
        "use_tabs": config.use_tabs,
        "line_ending": config.line_ending,
        "struct_case": config.struct_case,
        "field_case": config.field_case,
        "generate_json_tags": config.generate_json_tags,
        "json_tag_omitempty": config.json_tag_omitempty,
        "json_tag_case": config.json_tag_case,
        "add_comments": config.add_comments,
    }

    # Add language-specific settings
    config_dict.update(config.language_config)

    try:
        with open(path, "w", encoding="utf-8") as f:
            json.dump(config_dict, f, indent=2, ensure_ascii=False)
    except Exception as e:
        raise ConfigError(f"Failed to save configuration to {path}: {str(e)}")


def create_attention_config() -> GeneratorConfig:
    """Create configuration optimized for attention descriptions."""
    return GeneratorConfig(
        add_comments=True,
        generate_json_tags=True,
        json_tag_omitempty=True,
    )


def create_clean_config() -> GeneratorConfig:
    """Create configuration with minimal descriptions (clean output)."""
    return GeneratorConfig(
        add_comments=False,
        generate_json_tags=True,
        json_tag_omitempty=True,
    )
