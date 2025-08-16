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
from .templates import TemplateEngine, TemplateError, create_template_engine

__all__ = [
    # Base generator interface
    "CodeGenerator",
    "GeneratorError",
    "GenerationResult",
    "generate_code",
    # Schema system - core data structures
    "Schema",
    "Field",
    "FieldType",
    "convert_analyzer_output",
    "extract_all_schemas",
    # Naming utilities - language-agnostic
    "NameSanitizer",
    "NamingCase",
    # Configuration system
    "GeneratorConfig",
    "ConfigManager",
    "ConfigError",
    "load_config",
    # Template system - language-agnostic
    "TemplateEngine",
    "TemplateError",
    "create_template_engine",
]
