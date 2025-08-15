"""
Core code generation components.

Provides base classes and utilities used by all language generators.
"""

from .generator import CodeGenerator, GeneratorError, GenerationResult, generate_code
from .schema import (
    Schema,
    Field,
    FieldType,
    convert_analyzer_output,
    extract_all_schemas,
)
from .naming import NameSanitizer, NamingCase
from .config import GeneratorConfig, ConfigManager, ConfigError, load_config
from .templates import TemplateEngine, TemplateError, get_default_template_engine

__all__ = [
    # Base classes
    "CodeGenerator",
    "GeneratorError",
    "GenerationResult",
    # Schema system
    "Schema",
    "Field",
    "FieldType",
    "convert_analyzer_output",
    "extract_all_schemas",
    # Naming utilities
    "NameSanitizer",
    "NamingCase",
    # Configuration
    "GeneratorConfig",
    "ConfigManager",
    "ConfigError",
    "load_config",
    # Templates
    "TemplateEngine",
    "TemplateError",
    "get_default_template_engine",
    # Main function
    "generate_code",
]
