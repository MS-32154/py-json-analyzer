"""
Language-specific code generators.

This module contains generators for different programming languages.
Each language is in its own submodule with generator, config, and interactive handler.
"""

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)

# Track available languages
__all__ = []

# ============================================================================
# Go Generator
# ============================================================================

try:
    from .go import (
        GoConfig,
        GoGenerator,
        GoInteractiveHandler,
        create_go_generator,
        create_go_name_tracker,
        create_strict_generator,
        create_web_api_generator,
        get_modern_config,
        get_strict_config,
        get_web_api_config,
    )

    __all__.extend(
        [
            "GoGenerator",
            "GoConfig",
            "GoInteractiveHandler",
            "create_go_generator",
            "create_web_api_generator",
            "create_strict_generator",
            "create_go_name_tracker",
            "get_web_api_config",
            "get_strict_config",
            "get_modern_config",
        ]
    )

    logger.debug("Go generator module loaded successfully")

except ImportError as e:
    logger.debug(f"Go generator not available: {e}")
except Exception as e:
    logger.warning(f"Failed to import Go generator: {e}")


# ============================================================================
# Python Generator
# ============================================================================

try:
    from .python import (
        PythonConfig,
        PythonGenerator,
        PythonInteractiveHandler,
        PythonStyle,
        create_dataclass_generator,
        create_pydantic_generator,
        create_python_generator,
        create_python_name_tracker,
        create_typeddict_generator,
        get_dataclass_config,
        get_pydantic_config,
        get_strict_dataclass_config,
        get_typeddict_config,
    )

    __all__.extend(
        [
            "PythonGenerator",
            "PythonConfig",
            "PythonStyle",
            "PythonInteractiveHandler",
            "create_python_generator",
            "create_dataclass_generator",
            "create_pydantic_generator",
            "create_typeddict_generator",
            "create_python_name_tracker",
            "get_dataclass_config",
            "get_pydantic_config",
            "get_typeddict_config",
            "get_strict_dataclass_config",
        ]
    )

    logger.debug("Python generator module loaded successfully")

except ImportError as e:
    logger.debug(f"Python generator not available: {e}")
except Exception as e:
    logger.warning(f"Failed to import Python generator: {e}")


# ============================================================================
# Future Language Generators
# ============================================================================

# TypeScript Generator (Coming Soon)
# try:
#     from .typescript import (
#         TypeScriptGenerator,
#         TypeScriptConfig,
#         TypeScriptInteractiveHandler,
#         create_typescript_generator,
#     )
#
#     __all__.extend([
#         "TypeScriptGenerator",
#         "TypeScriptConfig",
#         "TypeScriptInteractiveHandler",
#         "create_typescript_generator",
#     ])
#
#     logger.debug("TypeScript generator module loaded successfully")
#
# except ImportError as e:
#     logger.debug(f"TypeScript generator not available: {e}")
# except Exception as e:
#     logger.warning(f"Failed to import TypeScript generator: {e}")


# Rust Generator (Coming Soon)
# try:
#     from .rust import (
#         RustGenerator,
#         RustConfig,
#         RustInteractiveHandler,
#         create_rust_generator,
#     )
#
#     __all__.extend([
#         "RustGenerator",
#         "RustConfig",
#         "RustInteractiveHandler",
#         "create_rust_generator",
#     ])
#
#     logger.debug("Rust generator module loaded successfully")
#
# except ImportError as e:
#     logger.debug(f"Rust generator not available: {e}")
# except Exception as e:
#     logger.warning(f"Failed to import Rust generator: {e}")


# ============================================================================
# Module Summary
# ============================================================================


def get_available_languages() -> list[str]:
    """
    Get list of available language generators.

    Returns:
        List of language names that have successfully loaded
    """
    available = []

    if "GoGenerator" in __all__:
        available.append("go")

    if "PythonGenerator" in __all__:
        available.append("python")

    # Future languages
    # if "TypeScriptGenerator" in __all__:
    #     available.append("typescript")
    # if "RustGenerator" in __all__:
    #     available.append("rust")

    return available


# Log summary on module import
_available = get_available_languages()
if _available:
    logger.info(f"Language generators loaded: {', '.join(_available)}")
else:
    logger.warning("No language generators available")
