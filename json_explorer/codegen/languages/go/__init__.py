"""
Go code generator module.

Generates Go structs with JSON tags from JSON schema analysis.
"""

from .generator import GoGenerator
from .naming import create_go_sanitizer, sanitize_go_struct_name, sanitize_go_field_name

# Default configuration
DEFAULT_CONFIG = {
    "package_name": "main",
    "use_pointers_for_optional": True,
    "generate_json_tags": True,
    "json_tag_omitempty": True,
    "struct_case": "pascal",
    "field_case": "pascal",
    "add_comments": True,
    "time_format": "RFC3339",
    "int_type": "int64",
    "float_type": "float64",
}


def create_generator(config=None):
    """Create a Go generator with optional configuration."""
    final_config = DEFAULT_CONFIG.copy()
    if config:
        final_config.update(config)
    return GoGenerator(final_config)


__all__ = [
    "GoGenerator",
    "create_generator",
    "DEFAULT_CONFIG",
    "create_go_sanitizer",
    "sanitize_go_struct_name",
    "sanitize_go_field_name",
]
