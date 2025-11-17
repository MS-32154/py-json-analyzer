"""
JSON Explorer Code Generation Module

Generates code in various languages from JSON schema analysis.
"""

# Import registry functions (this will trigger auto-registration)
from .registry import (
    GeneratorRegistry,
    get_generator,
    list_supported_languages,
    register_generator,
    get_language_info,
    list_all_language_info,
    is_language_supported,
    get_registry,
)

# Import core interfaces
from .core import (
    CodeGenerator,
    GeneratorError,
    GenerationResult,
    generate_code,
    Schema,
    Field,
    FieldType,
    convert_analyzer_output,
    extract_all_schemas,
    GeneratorConfig,
    load_config,
    NameSanitizer,
    NamingCase,
    TemplateEngine,
    TemplateError,
    create_template_engine,
)

# Version info
__version__ = "0.1.0"


def generate_from_analysis(
    analyzer_result, language="go", config=None, root_name="Root"
) -> GenerationResult:
    """
    Generate code from analyzer output.

    Args:
        analyzer_result: Output from json_explorer.analyzer.analyze_json()
        language: Target language name
        config: GeneratorConfig instance, dict, or path to config file
        root_name: Name for root schema

    Returns:
        GenerationResult with generated code and metadata
    """
    # Convert analyzer result to schema
    root_schema = convert_analyzer_output(analyzer_result, root_name)
    all_schemas = extract_all_schemas(root_schema)

    # Get generator instance
    generator = get_generator(language, config)

    # Generate code
    return generate_code(generator, all_schemas, root_name)


def quick_generate(json_data, language="go", **options) -> str:
    """
    Quick code generation from JSON data.

    Args:
        json_data: JSON data (dict/list/str)
        language: Target language
        **options: Generator configuration options

    Returns:
        Generated code string

    Raises:
        GeneratorError: If generation fails
    """
    from json_explorer.analyzer import analyze_json
    import json as json_module

    # Convert string to dict if needed
    if isinstance(json_data, str):
        try:
            json_data = json_module.loads(json_data)
        except json_module.JSONDecodeError as e:
            raise GeneratorError(f"Invalid JSON data: {e}")

    # Analyze JSON
    try:
        analysis = analyze_json(json_data)
    except Exception as e:
        raise GeneratorError(f"JSON analysis failed: {e}")

    # Generate code
    result = generate_from_analysis(analysis, language, options)

    if result.success:
        return result.code
    else:
        raise GeneratorError(f"Code generation failed: {result.error_message}")


def create_config(language="go", **kwargs) -> GeneratorConfig:
    """
    Create a GeneratorConfig for the specified language.

    Args:
        language: Target language
        **kwargs: Configuration options

    Returns:
        GeneratorConfig instance
    """
    return load_config(custom_config=kwargs)


# Export main interfaces
__all__ = [
    # Registry
    "GeneratorRegistry",
    "get_generator",
    "list_supported_languages",
    "register_generator",
    "get_language_info",
    "list_all_language_info",
    "is_language_supported",
    "get_registry",
    # Core interfaces
    "CodeGenerator",
    "GeneratorError",
    "GenerationResult",
    "generate_code",
    # Schema system
    "Schema",
    "Field",
    "FieldType",
    "convert_analyzer_output",
    "extract_all_schemas",
    # Configuration
    "GeneratorConfig",
    "load_config",
    "create_config",
    # Naming utilities
    "NameSanitizer",
    "NamingCase",
    # Template system
    "TemplateEngine",
    "TemplateError",
    "create_template_engine",
    # High-level API
    "generate_from_analysis",
    "quick_generate",
]
