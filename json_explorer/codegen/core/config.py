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
    field_case: str = "pascal"   # pascal, camel, snake
    constant_case: str = "screaming_snake"
    
    # Type handling
    use_pointers_for_optional: bool = True
    strict_types: bool = False
    
    # JSON settings
    generate_json_tags: bool = True
    json_tag_omitempty: bool = True
    json_tag_case: str = "original"  # original, snake, camel
    
    # Additional metadata
    add_comments: bool = True
    add_validation: bool = False
    
    # Custom settings (language-specific)
    custom: Dict[str, Any] = field(default_factory=dict)


class ConfigManager:
    """Manages configuration loading and merging."""
    
    def __init__(self):
        """Initialize configuration manager."""
        self._configs: Dict[str, Dict[str, Any]] = {}
        self._load_defaults()
    
    def _load_defaults(self):
        """Load default configurations for supported languages."""
        # Go defaults
        self._configs["go"] = {
            "package_name": "main",
            "struct_case": "pascal",
            "field_case": "pascal", 
            "use_pointers_for_optional": True,
            "generate_json_tags": True,
            "json_tag_omitempty": True,
            "json_tag_case": "original",
            "add_comments": True,
            "custom": {
                "time_format": "RFC3339",
                "int_type": "int64",
                "float_type": "float64"
            }
        }
        
        # Python defaults  
        self._configs["python"] = {
            "package_name": "",
            "struct_case": "pascal",
            "field_case": "snake",
            "use_pointers_for_optional": False,
            "generate_json_tags": False,
            "json_tag_omitempty": False,
            "json_tag_case": "snake",
            "add_comments": True,
            "custom": {
                "dataclass_style": "dataclass",  # dataclass, pydantic, attrs
                "optional_type": "Optional",
                "import_style": "from_typing"
            }
        }
    
    def get_config(self, language: str, custom_config: Optional[Dict[str, Any]] = None,
                   config_file: Optional[Union[str, Path]] = None) -> GeneratorConfig:
        """
        Get complete configuration for a language.
        
        Args:
            language: Target language name
            custom_config: Custom configuration overrides
            config_file: Path to JSON configuration file
            
        Returns:
            Merged configuration for the language
        """
        # Start with defaults
        base_config = self._configs.get(language, {}).copy()
        
        # Load from file if provided
        if config_file:
            file_config = self._load_config_file(config_file)
            base_config.update(file_config)
        
        # Apply custom overrides
        if custom_config:
            base_config.update(custom_config)
        
        # Create GeneratorConfig instance
        return self._dict_to_config(base_config)
    
    def _load_config_file(self, config_path: Union[str, Path]) -> Dict[str, Any]:
        """Load configuration from JSON file."""
        path = Path(config_path)
        
        if not path.exists():
            raise ConfigError(f"Configuration file not found: {path}")
        
        if not path.suffix.lower() == '.json':
            raise ConfigError(f"Configuration file must be JSON: {path}")
        
        try:
            with open(path, 'r', encoding='utf-8') as f:
                config = json.load(f)
            
            if not isinstance(config, dict):
                raise ConfigError(f"Configuration file must contain a JSON object: {path}")
            
            return config
            
        except json.JSONDecodeError as e:
            raise ConfigError(f"Invalid JSON in configuration file {path}: {str(e)}")
        except Exception as e:
            raise ConfigError(f"Failed to load configuration file {path}: {str(e)}")
    
    def _dict_to_config(self, config_dict: Dict[str, Any]) -> GeneratorConfig:
        """Convert dictionary to GeneratorConfig instance."""
        # Extract known fields
        known_fields = {f.name for f in GeneratorConfig.__dataclass_fields__.values()}
        
        config_args = {}
        custom_args = {}
        
        for key, value in config_dict.items():
            if key in known_fields:
                config_args[key] = value
            else:
                custom_args[key] = value
        
        # Add custom fields to the custom dict
        if custom_args:
            existing_custom = config_args.get('custom', {})
            existing_custom.update(custom_args)
            config_args['custom'] = existing_custom
        
        return GeneratorConfig(**config_args)
    
    def save_config(self, config: GeneratorConfig, output_path: Union[str, Path]):
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
            "constant_case": config.constant_case,
            "use_pointers_for_optional": config.use_pointers_for_optional,
            "strict_types": config.strict_types,
            "generate_json_tags": config.generate_json_tags,
            "json_tag_omitempty": config.json_tag_omitempty,
            "json_tag_case": config.json_tag_case,
            "add_comments": config.add_comments,
            "add_validation": config.add_validation,
        }
        
        # Add custom settings
        config_dict.update(config.custom)
        
        try:
            with open(path, 'w', encoding='utf-8') as f:
                json.dump(config_dict, f, indent=2, ensure_ascii=False)
        except Exception as e:
            raise ConfigError(f"Failed to save configuration to {path}: {str(e)}")
    
    def list_languages(self) -> list[str]:
        """Get list of supported languages."""
        return list(self._configs.keys())
    
    def validate_config(self, config: GeneratorConfig, language: str) -> list[str]:
        """
        Validate configuration for a language.
        
        Returns:
            List of validation warnings/errors
        """
        warnings = []
        
        # Validate case styles
        valid_cases = {"pascal", "camel", "snake", "screaming_snake"}
        
        if config.struct_case not in valid_cases:
            warnings.append(f"Invalid struct_case: {config.struct_case}")
        
        if config.field_case not in valid_cases:
            warnings.append(f"Invalid field_case: {config.field_case}")
        
        if config.json_tag_case not in {"original", "snake", "camel", "pascal"}:
            warnings.append(f"Invalid json_tag_case: {config.json_tag_case}")
        
        # Language-specific validations
        if language == "go":
            if config.package_name and not config.package_name.isidentifier():
                warnings.append(f"Invalid Go package name: {config.package_name}")
        
        elif language == "python":
            dataclass_style = config.custom.get("dataclass_style", "dataclass")
            valid_styles = {"dataclass", "pydantic", "attrs"}
            if dataclass_style not in valid_styles:
                warnings.append(f"Invalid dataclass_style: {dataclass_style}")
        
        return warnings


# Global configuration manager instance
_config_manager = None

def get_config_manager() -> ConfigManager:
    """Get the global configuration manager instance."""
    global _config_manager
    if _config_manager is None:
        _config_manager = ConfigManager()
    return _config_manager


def load_config(language: str, custom_config: Optional[Dict[str, Any]] = None,
                config_file: Optional[Union[str, Path]] = None) -> GeneratorConfig:
    """
    Convenience function to load configuration.
    
    Args:
        language: Target language name
        custom_config: Custom configuration overrides
        config_file: Path to JSON configuration file
        
    Returns:
        Merged configuration for the language
    """
    manager = get_config_manager()
    return manager.get_config(language, custom_config, config_file)


# Example configuration files for reference
EXAMPLE_GO_CONFIG = {
    "package_name": "models",
    "use_pointers_for_optional": True,
    "generate_json_tags": True,
    "json_tag_omitempty": True,
    "add_comments": True,
    "time_format": "RFC3339",
    "int_type": "int64"
}

EXAMPLE_PYTHON_CONFIG = {
    "dataclass_style": "pydantic",
    "field_case": "snake",
    "optional_type": "Optional",
    "add_validation": True,
    "import_style": "from_typing"
}
