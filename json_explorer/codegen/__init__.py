"""
JSON Explorer Code Generation Module.

Generates code in various languages from JSON schema analysis.

Example:
    >>> from json_explorer.codegen import quick_generate
    >>> code = quick_generate({"name": "John", "age": 30}, language="python")
    >>> print(code)
"""

from json_explorer.logging_config import get_logger

# Import core interfaces
from .core import (
    CodeGenerator,
    Field,
    FieldType,
    GenerationResult,
    GeneratorConfig,
    GeneratorError,
    NamePlan,
    Schema,
    TemplateError,
    TemplateManager,
    convert_analyzer_output,
    extract_all_schemas,
    generate_code,
    load_config,
    plan_names,
)

# Import registry functions
from .registry import (
    RegistryError,
    create_generator,
    get_aliases,
    get_generator,
    get_generator_class,
    get_language_info,
    is_language_supported,
    is_supported,
    list_all_language_info,
    list_languages,
    list_supported_languages,
    register,
)

logger = get_logger(__name__)

# ============================================================================
# High-Level API Functions
# ============================================================================


def generate_from_analysis(
    analyzer_result: dict,
    language: str = "go",
    config: GeneratorConfig | dict | str | None = None,
    root_name: str = "Root",
) -> GenerationResult:
    """
    Generate code from analyzer output.

    Args:
        analyzer_result: Output from json_explorer.analyzer.analyze_json()
        language: Target language name (e.g., 'go', 'python')
        config: Configuration (GeneratorConfig, dict, or file path)
        root_name: Name for root schema

    Returns:
        GenerationResult with generated code and metadata

    Example:
        >>> from json_explorer.analyzer import analyze_json
        >>> analysis = analyze_json({"name": "John", "age": 30})
        >>> result = generate_from_analysis(analysis, "python")
        >>> print(result.code)
    """
    logger.info("Generating %s code from analyzer result", language)

    # Convert analyzer result to schema
    root_schema = convert_analyzer_output(analyzer_result, root_name)
    all_schemas = extract_all_schemas(root_schema)

    logger.debug("Converted to %s schemas", len(all_schemas))

    # Get generator instance
    generator = get_generator(language, config)

    # Generate code
    return generate_code(generator, all_schemas, root_name)


def quick_generate(
    json_data: dict | list | str,
    language: str = "go",
    **options,
) -> str:
    """
    Quick code generation from JSON data.

    This is the simplest way to generate code from JSON.
    It handles analysis automatically.

    Args:
        json_data: JSON data (dict, list, or JSON string)
        language: Target language (e.g., 'go', 'python')
        **options: Generator configuration options

    Returns:
        Generated code string

    Raises:
        GeneratorError: If generation fails

    Example:
        >>> code = quick_generate(
        ...     {"user_id": 1, "name": "Alice"},
        ...     language="python",
        ...     style="dataclass",
        ... )
        >>> print(code)
    """
    import json as json_module

    from json_explorer.analyzer import analyze_json

    logger.info("Quick generate: %s", language)

    # Convert string to dict if needed
    if isinstance(json_data, str):
        try:
            json_data = json_module.loads(json_data)
        except json_module.JSONDecodeError as e:
            raise GeneratorError(f"Invalid JSON data: {e}") from e

    # Analyze JSON
    try:
        analysis = analyze_json(json_data)
    except Exception as e:
        raise GeneratorError(f"JSON analysis failed: {e}") from e

    # Apply language-specific defaults

    # Generate code
    result = generate_from_analysis(analysis, language, options)

    if result.success:
        logger.info("Quick generation completed successfully")
        return result.code
    raise GeneratorError(f"Code generation failed: {result.error_message}")


def create_config(language: str = "go", **kwargs) -> GeneratorConfig:
    """
    Create a GeneratorConfig for the specified language.

    Args:
        language: Target language
        **kwargs: Configuration options

    Returns:
        GeneratorConfig instance

    Example:
        >>> config = create_config(
        ...     "python",
        ...     package_name="models",
        ...     style="pydantic",
        ... )

    Raises:
        RegistryError: If the language is not supported
    """
    get_generator_class(language)  # raises RegistryError for unknown languages
    return load_config(custom_config=kwargs)


# ============================================================================
# Public API
# ============================================================================


__all__ = [
    "CodeGenerator",
    "Field",
    "FieldType",
    "GenerationResult",
    "GeneratorConfig",
    "GeneratorError",
    "NamePlan",
    "RegistryError",
    "Schema",
    "TemplateError",
    "TemplateManager",
    "convert_analyzer_output",
    "create_config",
    "create_generator",
    "extract_all_schemas",
    "generate_code",
    "generate_from_analysis",
    "get_aliases",
    "get_generator",
    "get_generator_class",
    "get_language_info",
    "is_language_supported",
    "is_supported",
    "list_all_language_info",
    "list_languages",
    "list_supported_languages",
    "load_config",
    "plan_names",
    "quick_generate",
    "register",
]
