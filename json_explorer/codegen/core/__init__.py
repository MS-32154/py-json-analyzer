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
from .naming import (
    CaseStyle,
    NameTracker,
    clean_identifier,
    convert_case,
    resolve_conflict,
    sanitize_name,
    to_camel_case,
    to_kebab_case,
    to_pascal_case,
    to_screaming_snake_case,
    to_snake_case,
)
from .schema import (
    Field,
    FieldType,
    Schema,
    convert_analyzer_output,
    extract_all_schemas,
    map_analyzer_type,
)
from .templates import (
    TemplateError,
    TemplateManager,
    create_template_env,
    list_templates,
    render_string,
    render_template,
    template_exists,
)

__all__ = [
    # Naming
    "CaseStyle",
    # Generator
    "CodeGenerator",
    # Configuration
    "ConfigError",
    "Field",
    "FieldType",
    "GenerationResult",
    "GeneratorConfig",
    "GeneratorError",
    "NameTracker",
    # Schema
    "Schema",
    "TemplateError",
    # Templates
    "TemplateManager",
    "clean_identifier",
    "convert_analyzer_output",
    "convert_case",
    "create_minimal_config",
    "create_strict_config",
    "create_template_env",
    "create_verbose_config",
    "extract_all_schemas",
    "generate_code",
    "list_templates",
    "load_config",
    "load_config_file",
    "map_analyzer_type",
    "render_string",
    "render_template",
    "resolve_conflict",
    "sanitize_name",
    "save_config",
    "template_exists",
    "to_camel_case",
    "to_kebab_case",
    "to_pascal_case",
    "to_screaming_snake_case",
    "to_snake_case",
    "validate_language_config",
]
