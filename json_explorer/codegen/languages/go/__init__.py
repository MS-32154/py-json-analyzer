"""
Go code generator module.

Generates Go structs with JSON tags from JSON schema analysis.
"""

from .config import (
    GoConfig,
    get_modern_config,
    get_strict_config,
    get_web_api_config,
)
from .generator import (
    GoGenerator,
    create_go_generator,
    create_strict_generator,
    create_web_api_generator,
)
from .interactive import GoInteractiveHandler
from .naming import create_go_name_tracker

__all__ = [
    # Generator
    "GoGenerator",
    "create_go_generator",
    "create_web_api_generator",
    "create_strict_generator",
    # Configuration
    "GoConfig",
    "get_web_api_config",
    "get_strict_config",
    "get_modern_config",
    # Naming
    "create_go_name_tracker",
    # Interactive
    "GoInteractiveHandler",
]
