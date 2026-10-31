"""
Core code generation components.

Provides base classes and utilities used by all language generators.
"""

from .config import (
    ConfigError,
    GeneratorConfig,
    create_minimal_config,
    create_strict_config,
    create_verbose_config,
    load_config,
    load_config_file,
    save_config,
    validate_language_config,
)
from .generator import (
    CodeGenerator,
    GenerationResult,
    GeneratorError,
    generate_code,
)
from .naming import NameTracker, sanitize_name, to_pascal_case, to_snake_case
from .schema import (
    Field,
    FieldType,
    Schema,
    convert_analyzer_output,
    extract_all_schemas,
    map_analyzer_type,
)
from .templates import TemplateError, TemplateManager

__all__ = [
    "CodeGenerator",
    "ConfigError",
    "Field",
    "FieldType",
    "GenerationResult",
    "GeneratorConfig",
    "GeneratorError",
    "NameTracker",
    "Schema",
    "TemplateError",
    "TemplateManager",
    "convert_analyzer_output",
    "create_minimal_config",
    "create_strict_config",
    "create_verbose_config",
    "extract_all_schemas",
    "generate_code",
    "load_config",
    "load_config_file",
    "map_analyzer_type",
    "sanitize_name",
    "save_config",
    "to_pascal_case",
    "to_snake_case",
    "validate_language_config",
]
