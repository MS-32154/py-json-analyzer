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
    # Configuration
    "ConfigError",
    "GeneratorConfig",
    "load_config",
    "load_config_file",
    "save_config",
    "create_minimal_config",
    "create_verbose_config",
    "create_strict_config",
    "validate_language_config",
    # Generator
    "CodeGenerator",
    "GeneratorError",
    "GenerationResult",
    "generate_code",
    # Schema
    "Schema",
    "Field",
    "FieldType",
    "convert_analyzer_output",
    "extract_all_schemas",
    "map_analyzer_type",
    # Naming
    "CaseStyle",
    "NameTracker",
    "sanitize_name",
    "clean_identifier",
    "convert_case",
    "resolve_conflict",
    "to_snake_case",
    "to_camel_case",
    "to_pascal_case",
    "to_kebab_case",
    "to_screaming_snake_case",
    # Templates
    "TemplateManager",
    "TemplateError",
    "create_template_env",
    "render_template",
    "render_string",
    "template_exists",
    "list_templates",
]
