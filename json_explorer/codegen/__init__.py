"""
JSON Explorer Code Generation Module.

Generates code in various languages from JSON schema analysis.

Example:
    >>> from json_explorer.codegen import quick_generate
    >>> code = quick_generate({"name": "John", "age": 30}, language="python")
    >>> print(code)
"""

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)

# Import core interfaces
from .core import (
    CodeGenerator,
    Field,
    FieldType,
    GenerationResult,
    GeneratorConfig,
    GeneratorError,
    NameTracker,
    Schema,
    TemplateError,
    TemplateManager,
    convert_analyzer_output,
    create_template_env,
    extract_all_schemas,
    generate_code,
    load_config,
    sanitize_name,
)

# Import registry functions
from .registry import (
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
    logger.info(f"Generating {language} code from analyzer result")

    # Convert analyzer result to schema
    root_schema = convert_analyzer_output(analyzer_result, root_name)
    all_schemas = extract_all_schemas(root_schema)

    logger.debug(f"Converted to {len(all_schemas)} schemas")

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
    from json_explorer.analyzer import analyze_json
    import json as json_module

    logger.info(f"Quick generate: {language}")

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

    # Apply language-specific defaults
    if language.lower() in ("python", "py"):
        # Python uses snake_case for fields by default
        if "field_case" not in options:
            options["field_case"] = "snake"

    # Generate code
    result = generate_from_analysis(analysis, language, options)

    if result.success:
        logger.info("Quick generation completed successfully")
        return result.code
    else:
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
    """
    return load_config(custom_config=kwargs)


# ============================================================================
# Public API
# ============================================================================


__all__ = [
    # High-level API
    "generate_from_analysis",
    "quick_generate",
    "create_config",
    # Registry
    "register",
    "get_generator",
    "create_generator",
    "get_generator_class",
    "list_languages",
    "list_supported_languages",
    "is_supported",
    "is_language_supported",
    "get_aliases",
    "get_language_info",
    "list_all_language_info",
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
    # Naming utilities
    "NameTracker",
    "sanitize_name",
    # Template system
    "TemplateManager",
    "TemplateError",
    "create_template_env",
]
