"""
Go code generator module.

Generates Go structs with JSON tags from JSON schema analysis.
Fully integrated with the new type system for flexible type mapping.
"""

from .generator import GoGenerator
from .naming import create_go_sanitizer
from .types import (
    GoType,
    GoTypeConfig,
    GoTypeMapper,
    ConflictStrategy,
    PointerStrategy,
    create_web_api_type_config,
    create_strict_type_config,
    create_modern_go_type_config,
)

# Export type system components
__all__ = [
    "GoGenerator",
    "GoType",
    "GoTypeConfig",
    "GoTypeMapper",
    "ConflictStrategy",
    "PointerStrategy",
    "create_go_sanitizer",
    # Factory functions
    "create_generator",
    "create_web_api_generator",
    "create_strict_generator",
    "create_modern_go_generator",
    "create_cli_tool_generator",
    "create_library_generator",
    # Type config factories
    "create_web_api_type_config",
    "create_strict_type_config",
    "create_modern_go_type_config",
]


def create_generator(type_config: GoTypeConfig = None, **kwargs):
    """
    Create a Go generator with type configuration.

    Args:
        type_config: GoTypeConfig instance for type mapping behavior
        **kwargs: Additional generator options (package_name, generate_json_tags, etc.)

    Returns:
        Configured GoGenerator instance
    """
    if type_config is None:
        type_config = GoTypeConfig()  # Use defaults

    # Build generator config with type system
    generator_config = {
        "package_name": kwargs.get("package_name", "main"),
        "generate_json_tags": kwargs.get("generate_json_tags", True),
        "add_comments": kwargs.get("add_comments", True),
        "type_config": type_config,
        **kwargs,  # Allow other options to be passed through
    }

    return GoGenerator(generator_config)


def create_web_api_generator():
    """
    Create generator optimized for web API models.

    Features:
    - Uses pointers for optional fields
    - Includes JSON tags with omitempty
    - Uses int64/float64 for numbers
    - Handles conflicts with interface{}
    """
    return GoGenerator(
        {
            "package_name": "models",
            "generate_json_tags": True,
            "add_comments": True,
            "type_config": create_web_api_type_config(),
        }
    )


def create_strict_generator():
    """
    Create generator with strict type checking.

    Features:
    - Never uses pointers
    - Fails on type conflicts
    - No omitempty JSON tags
    - Strict validation
    """
    return GoGenerator(
        {
            "package_name": "types",
            "generate_json_tags": True,
            "add_comments": True,
            "type_config": create_strict_type_config(),
        }
    )


def create_modern_go_generator():
    """
    Create generator using modern Go 1.18+ features.

    Features:
    - Uses 'any' instead of interface{}
    - Modern Go conventions
    - Smart pointer usage
    """
    return GoGenerator(
        {
            "package_name": "types",
            "generate_json_tags": True,
            "add_comments": True,
            "type_config": create_modern_go_type_config(),
        }
    )


def create_cli_tool_generator():
    """
    Create generator optimized for CLI tools.

    Features:
    - Package main
    - No JSON tags
    - Simple types, no pointers
    - Minimal comments
    """
    type_config = GoTypeConfig(
        pointer_strategy=PointerStrategy.NEVER,
        conflict_strategy=ConflictStrategy.FIRST_TYPE,
        omit_empty_optional=False,
    )

    return GoGenerator(
        {
            "package_name": "main",
            "generate_json_tags": False,
            "add_comments": False,
            "type_config": type_config,
        }
    )


def create_library_generator():
    """
    Create generator optimized for reusable libraries.

    Features:
    - Package types
    - JSON tags without omitempty
    - No pointers for better API
    - Extensive comments
    - Interface{} for flexibility
    """
    type_config = GoTypeConfig(
        pointer_strategy=PointerStrategy.NEVER,
        conflict_strategy=ConflictStrategy.INTERFACE,
        omit_empty_optional=False,
    )

    return GoGenerator(
        {
            "package_name": "types",
            "generate_json_tags": True,
            "add_comments": True,
            "type_config": type_config,
        }
    )


# Example usage patterns:
#
# Basic generator:
# generator = create_generator()
#
# Custom type config:
# type_config = GoTypeConfig(int_type="int32", pointer_strategy=PointerStrategy.NEVER)
# generator = create_generator(type_config=type_config, package_name="models")
#
# Use presets:
# generator = create_web_api_generator()  # Pre-configured for web APIs
