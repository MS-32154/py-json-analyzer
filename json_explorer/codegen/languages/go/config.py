"""
Go-specific configuration and validation.

Extends the base configuration system with Go-specific settings.
"""

from typing import Dict, Any, List
from json_explorer.codegen.core.config import GeneratorConfig


class GoConfig(GeneratorConfig):
    """Go-specific configuration."""

    def __init__(self, **kwargs):
        """Initialize Go configuration with defaults."""
        super().__init__(**kwargs)

        # Go-specific defaults
        if not self.custom:
            self.custom = {}

        # Set Go defaults
        self.custom.setdefault("time_format", "RFC3339")
        self.custom.setdefault("int_type", "int64")
        self.custom.setdefault("float_type", "float64")
        self.custom.setdefault("string_type", "string")
        self.custom.setdefault("bool_type", "bool")

        # Validate Go-specific settings
        self._validate_go_settings()

    def _validate_go_settings(self):
        """Validate Go-specific configuration."""
        # Validate time format
        valid_time_formats = {
            "RFC3339",
            "RFC3339Nano",
            "RFC822",
            "RFC822Z",
            "RFC850",
            "RFC1123",
            "RFC1123Z",
            "Kitchen",
            "Stamp",
            "StampMilli",
            "StampMicro",
            "StampNano",
        }

        time_format = self.custom.get("time_format")
        if time_format and time_format not in valid_time_formats:
            raise ValueError(f"Invalid time_format: {time_format}")

        # Validate numeric types
        valid_int_types = {"int", "int8", "int16", "int32", "int64"}
        int_type = self.custom.get("int_type")
        if int_type and int_type not in valid_int_types:
            raise ValueError(f"Invalid int_type: {int_type}")

        valid_float_types = {"float32", "float64"}
        float_type = self.custom.get("float_type")
        if float_type and float_type not in valid_float_types:
            raise ValueError(f"Invalid float_type: {float_type}")


def get_go_type_imports(fields_data: List[Dict[str, Any]]) -> List[str]:
    """
    Determine what imports are needed based on field types.

    Args:
        fields_data: List of field information

    Returns:
        List of import statements needed
    """
    imports = set()

    for field in fields_data:
        field_type = field.get("type", "")

        # Time package
        if "time.Time" in field_type:
            imports.add('"time"')

        # JSON package (if using custom marshal/unmarshal)
        if field.get("needs_json_import"):
            imports.add('"encoding/json"')

        # String manipulation
        if field.get("needs_strings_import"):
            imports.add('"strings"')

        # Regex
        if field.get("needs_regexp_import"):
            imports.add('"regexp"')

    return sorted(imports)


def format_go_imports(imports: List[str]) -> str:
    """Format import statements for Go."""
    if not imports:
        return ""

    if len(imports) == 1:
        return f"import {imports[0]}\n"

    # Multiple imports
    lines = ["import ("]
    for imp in imports:
        lines.append(f"\t{imp}")
    lines.append(")\n")

    return "\n".join(lines)


# Default configurations for different Go use cases
WEB_API_CONFIG = {
    "package_name": "models",
    "generate_json_tags": True,
    "json_tag_omitempty": True,
    "use_pointers_for_optional": True,
    "add_comments": True,
    "add_validation": True,
    "time_format": "RFC3339",
}

CLI_TOOL_CONFIG = {
    "package_name": "main",
    "generate_json_tags": False,
    "use_pointers_for_optional": False,
    "add_comments": False,
    "time_format": "RFC3339",
}

LIBRARY_CONFIG = {
    "package_name": "types",
    "generate_json_tags": True,
    "json_tag_omitempty": False,
    "use_pointers_for_optional": False,
    "add_comments": True,
    "add_validation": False,
    "time_format": "RFC3339",
}
