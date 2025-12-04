"""
Go-specific configuration and type mappings.
"""

from dataclasses import dataclass, field
from typing import Literal

from ...core.schema import FieldType

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Type Mappings
# ============================================================================


# Go type mapping for field types
GO_TYPE_MAP: dict[FieldType, str] = {
    FieldType.STRING: "string",
    FieldType.INTEGER: "int64",
    FieldType.FLOAT: "float64",
    FieldType.BOOLEAN: "bool",
    FieldType.TIMESTAMP: "time.Time",
    FieldType.UNKNOWN: "interface{}",
    FieldType.CONFLICT: "interface{}",
}

# Types that require imports
GO_IMPORTS: dict[str, str] = {
    "time.Time": '"time"',
}


# ============================================================================
# Go-Specific Configuration
# ============================================================================


@dataclass(slots=True, kw_only=True)
class GoConfig:
    """
    Go-specific configuration options.

    Attributes:
        int_type: Integer type to use (int, int32, int64)
        float_type: Float type to use (float32, float64)
        string_type: String type (always "string")
        bool_type: Boolean type (always "bool")
        time_type: Time type (time.Time, string, int64)
        unknown_type: Type for unknown/conflict (interface{}, any)
        use_pointers_for_optional: Use pointers (*T) for optional fields
    """

    # Type preferences
    int_type: Literal["int", "int32", "int64"] = "int64"
    float_type: Literal["float32", "float64"] = "float64"
    string_type: str = "string"
    bool_type: str = "bool"
    time_type: Literal["time.Time", "string", "int64"] = "time.Time"
    unknown_type: Literal["interface{}", "any"] = "interface{}"

    # Code generation options
    use_pointers_for_optional: bool = True

    # Declaration
    type_map: dict = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        """Build type map with configured types."""
        type_map = GO_TYPE_MAP.copy()
        type_map[FieldType.INTEGER] = self.int_type
        type_map[FieldType.FLOAT] = self.float_type
        type_map[FieldType.STRING] = self.string_type
        type_map[FieldType.BOOLEAN] = self.bool_type
        type_map[FieldType.TIMESTAMP] = self.time_type
        type_map[FieldType.UNKNOWN] = self.unknown_type
        type_map[FieldType.CONFLICT] = self.unknown_type

        object.__setattr__(self, "type_map", type_map)

        logger.debug(
            f"GoConfig initialized: int={self.int_type}, "
            f"float={self.float_type}, pointers={self.use_pointers_for_optional}"
        )

    def to_dict(self) -> dict:
        """Convert to dict, excluding computed fields."""
        return {
            "int_type": self.int_type,
            "float_type": self.float_type,
            "string_type": self.string_type,
            "bool_type": self.bool_type,
            "time_type": self.time_type,
            "unknown_type": self.unknown_type,
            "use_pointers_for_optional": self.use_pointers_for_optional,
        }

    def get_go_type(
        self,
        field_type: FieldType | None,
        *,
        is_optional: bool = False,
        is_array: bool = False,
        element_type: str | None = None,
    ) -> str:
        """
        Get Go type string for a field.

        Args:
            field_type: Field type enum
            is_optional: Whether field is optional
            is_array: Whether field is an array
            element_type: For arrays, the element type string

        Returns:
            Go type string (e.g., "string", "*int64", "[]User")
        """
        if is_array:
            base = (
                element_type or self.type_map.get(field_type, self.unknown_type)
                if field_type
                else self.unknown_type
            )
            return f"[]{base}"

        # Handle None field_type
        if field_type is None:
            go_type = self.unknown_type
        else:
            go_type = self.type_map.get(field_type, self.unknown_type)

        # Add pointer for optional fields if configured
        if is_optional and self.use_pointers_for_optional:
            # Don't add pointer to interface{}, any, or arrays
            if not go_type.startswith("[]") and go_type not in {"interface{}", "any"}:
                return f"*{go_type}"

        return go_type

    def get_required_imports(self, types_used: set[str]) -> list[str]:
        """
        Get required imports for the given types.

        Args:
            types_used: Set of Go types used in generated code

        Returns:
            Sorted list of import statements
        """
        imports = set()

        for go_type in types_used:
            # Remove pointer and array prefixes
            clean_type = go_type.lstrip("*").lstrip("[]")

            if clean_type in GO_IMPORTS:
                imports.add(GO_IMPORTS[clean_type])

        result = sorted(imports)
        logger.debug(f"Required imports: {len(result)}")
        return result


# ============================================================================
# Preset Configurations
# ============================================================================


def get_web_api_config() -> GoConfig:
    """
    Configuration optimized for web API models.

    - int64/float64 for JSON compatibility
    - Pointers for optional fields
    - time.Time for timestamps
    """
    return GoConfig(
        int_type="int64",
        float_type="float64",
        use_pointers_for_optional=True,
        time_type="time.Time",
    )


def get_strict_config() -> GoConfig:
    """
    Configuration with strict types (no pointers).

    - No pointers (all value types)
    - Suitable for performance-critical code
    """
    return GoConfig(
        use_pointers_for_optional=False,
    )


def get_modern_config() -> GoConfig:
    """
    Configuration using modern Go features (1.18+).

    - 'any' instead of interface{}
    - 'int' instead of int64
    """
    return GoConfig(
        unknown_type="any",
        int_type="int",
    )


def get_minimal_config() -> GoConfig:
    """
    Minimal configuration for simple use cases.

    - Basic types (int, float64)
    - No pointers
    - string for timestamps
    """
    return GoConfig(
        int_type="int",
        float_type="float64",
        time_type="string",
        use_pointers_for_optional=False,
    )
