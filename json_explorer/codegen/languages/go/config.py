"""
Go-specific configuration and type mappings.

Provides simple type mapping and Go-specific configuration.
"""

from typing import Set
from ...core.schema import FieldType
from .naming import GO_BUILTIN_TYPES, GO_RESERVED_WORDS


# Go type mappings
GO_TYPE_MAP = {
    FieldType.STRING: "string",
    FieldType.INTEGER: "int64",
    FieldType.FLOAT: "float64",
    FieldType.BOOLEAN: "bool",
    FieldType.TIMESTAMP: "time.Time",
    FieldType.UNKNOWN: "interface{}",
    FieldType.CONFLICT: "interface{}",
}

# Types that require imports
GO_IMPORT_MAP = {"time.Time": '"time"'}


class GoConfig:
    """Go-specific configuration."""

    def __init__(self, **kwargs):
        """Initialize Go configuration."""
        # Type preferences
        self.int_type = kwargs.get("int_type", "int64")
        self.float_type = kwargs.get("float_type", "float64")
        self.string_type = kwargs.get("string_type", "string")
        self.bool_type = kwargs.get("bool_type", "bool")
        self.time_type = kwargs.get("time_type", "time.Time")
        self.unknown_type = kwargs.get("unknown_type", "interface{}")

        # Pointer settings
        self.use_pointers_for_optional = kwargs.get("use_pointers_for_optional", True)

        # Build type map with configured types
        self.type_map = GO_TYPE_MAP.copy()
        self.type_map[FieldType.INTEGER] = self.int_type
        self.type_map[FieldType.FLOAT] = self.float_type
        self.type_map[FieldType.STRING] = self.string_type
        self.type_map[FieldType.BOOLEAN] = self.bool_type
        self.type_map[FieldType.TIMESTAMP] = self.time_type
        self.type_map[FieldType.UNKNOWN] = self.unknown_type
        self.type_map[FieldType.CONFLICT] = self.unknown_type

    def get_go_type(
        self,
        field_type: FieldType,
        is_optional: bool = False,
        is_array: bool = False,
        element_type: str = None,
    ) -> str:
        """Get Go type string for a field type."""
        if is_array:
            if element_type:
                base_type = element_type
            else:
                base_type = self.type_map.get(field_type, self.unknown_type)
            go_type = f"[]{base_type}"
        else:
            go_type = self.type_map.get(field_type, self.unknown_type)

        # Add pointer for optional fields if configured
        if is_optional and self.use_pointers_for_optional and not is_array:
            if not go_type.startswith("[]") and go_type not in ["interface{}", "any"]:
                go_type = f"*{go_type}"

        return go_type

    def get_required_imports(self, types_used: Set[str]) -> Set[str]:
        """Get required imports for the given types."""
        imports = set()
        for go_type in types_used:
            # Remove pointer prefix and array prefix
            clean_type = go_type.lstrip("*").lstrip("[]")
            if clean_type in GO_IMPORT_MAP:
                imports.add(GO_IMPORT_MAP[clean_type])
        return imports


def get_go_reserved_words() -> Set[str]:
    """Get Go reserved words."""
    return GO_RESERVED_WORDS


def get_go_builtin_types() -> Set[str]:
    """Get Go builtin types."""
    return GO_BUILTIN_TYPES


# Default configurations for different use cases
def get_web_api_config() -> GoConfig:
    """Configuration optimized for web API models."""
    return GoConfig(
        int_type="int64", float_type="float64", use_pointers_for_optional=True
    )


def get_strict_config() -> GoConfig:
    """Configuration with strict types (no pointers)."""
    return GoConfig(use_pointers_for_optional=False)


def get_modern_config() -> GoConfig:
    """Configuration using modern Go features."""
    return GoConfig(
        unknown_type="any", int_type="int"  # Go 1.18+  # Modern Go prefers int
    )
