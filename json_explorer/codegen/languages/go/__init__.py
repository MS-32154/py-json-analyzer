"""
Go code generator module.

Generates Go structs with JSON tags from JSON schema analysis.
"""

from .generator import (
    GoGenerator,
    create_go_generator,
    create_web_api_generator,
    create_strict_generator,
)
from .naming import create_go_sanitizer
from .config import (
    GoConfig,
    get_go_reserved_words,
    get_go_builtin_types,
    get_web_api_config,
    get_strict_config,
    get_modern_config,
)

from .interactive import GoInteractiveHandler

__all__ = [
    # Generator
    "GoGenerator",
    "create_go_generator",
    "create_web_api_generator",
    "create_strict_generator",
    # Naming
    "create_go_sanitizer",
    # Configuration
    "GoConfig",
    "get_go_reserved_words",
    "get_go_builtin_types",
    "get_web_api_config",
    "get_strict_config",
    "get_modern_config",
    # Interactive
    "GoInteractiveHandler",
]
