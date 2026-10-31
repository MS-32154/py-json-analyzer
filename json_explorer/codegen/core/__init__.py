"""
Core code generation components.

Provides base classes and utilities used by all language generators.
"""

from .config import (
    ConfigError,
    GeneratorConfig,
    load_config,
    save_config,
)
from .generator import (
    CodeGenerator,
    GenerationResult,
    GeneratorError,
    generate_code,
)
from .naming import NamePlan, plan_names, split_words, to_pascal_case, to_snake_case
from .schema import (
    Field,
    FieldType,
    Schema,
    convert_analyzer_output,
    extract_all_schemas,
    field_type_of,
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
    "NamePlan",
    "Schema",
    "TemplateError",
    "TemplateManager",
    "convert_analyzer_output",
    "extract_all_schemas",
    "field_type_of",
    "generate_code",
    "load_config",
    "plan_names",
    "save_config",
    "split_words",
    "to_pascal_case",
    "to_snake_case",
]
