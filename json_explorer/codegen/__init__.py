"""
JSON Explorer Code Generation Module

Generates code in various languages from JSON schema analysis.
"""

from .registry import GeneratorRegistry, get_generator, list_supported_languages
from .core.generator import CodeGenerator, GenerationResult, generate_code
from .core.schema import (
    Schema,
    Field,
    FieldType,
    convert_analyzer_output,
    extract_all_schemas,
)
from .core.config import GeneratorConfig, ConfigManager, load_config

# Initialize registry with available generators
registry = GeneratorRegistry()

# Auto-register available generators
try:
    from .languages.go.generator import GoGenerator

    registry.register("go", GoGenerator)
except ImportError:
    pass

# Version info
__version__ = "0.1.0"


# Convenience functions
def generate_from_analysis(
    analyzer_result, language="go", config=None, root_name="Root"
):
    """
    Generate code from analyzer output.

    Args:
        analyzer_result: Output from json_explorer.analyzer.analyze_json()
        language: Target language name
        config: Generator configuration dict or path
        root_name: Name for root schema

    Returns:
        GenerationResult with generated code
    """
    # Convert analyzer result to schema
    root_schema = convert_analyzer_output(analyzer_result, root_name)
    all_schemas = extract_all_schemas(root_schema)

    # Get generator
    generator = get_generator(language, config)

    # Generate code
    return generate_code(generator, all_schemas, root_name)


def quick_generate(json_data, language="go", **options):
    """
    Quick code generation from JSON data.

    Args:
        json_data: JSON data (dict/list/str)
        language: Target language
        **options: Generator options

    Returns:
        Generated code string
    """
    from json_explorer.analyzer import analyze_json

    # Convert string to dict if needed
    if isinstance(json_data, str):
        import json

        json_data = json.loads(json_data)

    # Analyze JSON
    analysis = analyze_json(json_data)

    # Generate code
    result = generate_from_analysis(analysis, language, options)

    if result.success:
        return result.code
    else:
        raise RuntimeError(f"Code generation failed: {result.error_message}")


# Export main interfaces
__all__ = [
    "GeneratorRegistry",
    "CodeGenerator",
    "GenerationResult",
    "Schema",
    "Field",
    "FieldType",
    "GeneratorConfig",
    "generate_from_analysis",
    "quick_generate",
    "get_generator",
    "list_supported_languages",
    "registry",
]
