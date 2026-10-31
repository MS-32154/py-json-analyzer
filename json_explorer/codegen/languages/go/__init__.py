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
from .naming import go_identifier, go_json_tag

__all__ = [
    "GoConfig",
    "GoGenerator",
    "GoInteractiveHandler",
    "create_go_generator",
    "create_strict_generator",
    "create_web_api_generator",
    "get_modern_config",
    "get_strict_config",
    "get_web_api_config",
    "go_identifier",
    "go_json_tag",
]
