"""
Go-specific type system for code generation.

Provides clean, extensible type mapping with configuration-driven behavior.
"""

from dataclasses import dataclass, field
from typing import Set, List, Dict, Optional, Any, Union
from enum import Enum

from ...core.schema import Field, FieldType


class ConflictStrategy(Enum):
    """Strategies for handling type conflicts."""

    INTERFACE = "interface"  # Use interface{}
    ANY = "any"  # Use any (Go 1.18+)
    STRICT = "strict"  # Fail with error
    FIRST_TYPE = "first_type"  # Use the first detected type


class PointerStrategy(Enum):
    """Strategies for using pointers in Go."""

    OPTIONAL_ONLY = "optional_only"  # Pointers only for optional fields
    ALWAYS = "always"  # Always use pointers for structs
    NEVER = "never"  # Never use pointers
    SMART = "smart"  # Intelligent pointer usage


@dataclass(frozen=True)
class GoType:
    """
    Immutable representation of a Go type with all metadata.

    This is the core type representation that carries everything needed
    to generate proper Go code with imports, validation, etc.
    """

    name: str  # The Go type name (e.g., "string", "*User")
    base_name: str = field(default="")  # Base name without pointer (e.g., "User")
    is_pointer: bool = field(default=False)  # Whether this is a pointer type
    imports_needed: Set[str] = field(default_factory=set)  # Required imports
    is_nilable: bool = field(default=False)  # Can be nil/zero value
    is_exported: bool = field(default=True)  # Should be exported (capitalized)
    validation_hints: List[str] = field(default_factory=list)  # Warnings/suggestions
    custom_json_tag: Optional[str] = field(default=None)  # Custom JSON tag options

    def __post_init__(self):
        """Set base_name if not provided."""
        if not self.base_name:
            # Remove pointer prefix to get base name
            base = self.name.lstrip("*")
            object.__setattr__(self, "base_name", base)

    def as_pointer(self) -> "GoType":
        """Return a pointer version of this type."""
        if self.is_pointer:
            return self  # Already a pointer

        return GoType(
            name=f"*{self.name}",
            base_name=self.base_name,
            is_pointer=True,
            imports_needed=self.imports_needed,
            is_nilable=True,
            is_exported=self.is_exported,
            validation_hints=self.validation_hints,
            custom_json_tag=self.custom_json_tag,
        )

    def as_non_pointer(self) -> "GoType":
        """Return a non-pointer version of this type."""
        if not self.is_pointer:
            return self  # Already non-pointer

        return GoType(
            name=self.base_name,
            base_name=self.base_name,
            is_pointer=False,
            imports_needed=self.imports_needed,
            is_nilable=False,
            is_exported=self.is_exported,
            validation_hints=self.validation_hints,
            custom_json_tag=self.custom_json_tag,
        )

    def with_validation_hint(self, hint: str) -> "GoType":
        """Add a validation hint to this type."""
        new_hints = list(self.validation_hints) + [hint]
        return GoType(
            name=self.name,
            base_name=self.base_name,
            is_pointer=self.is_pointer,
            imports_needed=self.imports_needed,
            is_nilable=self.is_nilable,
            is_exported=self.is_exported,
            validation_hints=new_hints,
            custom_json_tag=self.custom_json_tag,
        )


@dataclass
class GoTypeConfig:
    """Configuration for Go type mapping behavior."""

    # Numeric type preferences
    int_type: str = "int64"
    float_type: str = "float64"

    # String and basic types
    string_type: str = "string"
    bool_type: str = "bool"

    # Time handling
    time_type: str = "time.Time"  # or "string" for string timestamps
    time_import: str = "time"

    # Pointer usage strategy
    pointer_strategy: PointerStrategy = PointerStrategy.OPTIONAL_ONLY

    # Conflict resolution
    conflict_strategy: ConflictStrategy = ConflictStrategy.INTERFACE

    # Interface types
    unknown_type: str = "interface{}"  # or "any" for Go 1.18+

    # Custom type overrides
    type_overrides: Dict[FieldType, str] = field(default_factory=dict)

    # JSON tag preferences
    omit_empty_optional: bool = True

    def get_numeric_type(self, field_type: FieldType) -> str:
        """Get the configured numeric type."""
        if field_type == FieldType.INTEGER:
            return self.int_type
        elif field_type == FieldType.FLOAT:
            return self.float_type
        else:
            raise ValueError(f"Not a numeric type: {field_type}")


class GoTypeMapper:
    """
    Central engine for mapping JSON schema fields to Go types.

    This class handles all the complex logic of type mapping, conflict resolution,
    and Go-specific type decisions in a clean, testable way.
    """

    def __init__(self, config: Optional[GoTypeConfig] = None):
        """Initialize with type configuration."""
        self.config = config or GoTypeConfig()
        self._primitive_types = self._build_primitive_type_map()

    def _build_primitive_type_map(self) -> Dict[FieldType, GoType]:
        """Build mapping of primitive field types to Go types."""
        return {
            FieldType.STRING: GoType(name=self.config.string_type, is_nilable=False),
            FieldType.INTEGER: GoType(name=self.config.int_type, is_nilable=False),
            FieldType.FLOAT: GoType(name=self.config.float_type, is_nilable=False),
            FieldType.BOOLEAN: GoType(name=self.config.bool_type, is_nilable=False),
            FieldType.TIMESTAMP: GoType(
                name=self.config.time_type,
                imports_needed={f'"{self.config.time_import}"'},
                is_nilable=False,
            ),
        }

    def map_field_type(self, field: Field, struct_name_hint: str = "") -> GoType:
        """
        Map a schema field to a Go type.

        Args:
            field: The field to map
            struct_name_hint: Context hint for generating nested struct names

        Returns:
            Complete GoType with all metadata
        """
        # Handle type overrides first
        if field.type in self.config.type_overrides:
            override_type = self.config.type_overrides[field.type]
            base_type = GoType(name=override_type)
        else:
            base_type = self._map_base_type(field, struct_name_hint)

        # Apply pointer logic for optional fields
        final_type = self._apply_pointer_strategy(base_type, field)

        # Add validation hints if needed
        final_type = self._add_validation_hints(final_type, field)

        return final_type

    def _map_base_type(self, field: Field, struct_name_hint: str) -> GoType:
        """Map the base type without considering optionality."""

        # Primitive types
        if field.type in self._primitive_types:
            return self._primitive_types[field.type]

        # Array types
        elif field.type == FieldType.ARRAY:
            return self._map_array_type(field, struct_name_hint)

        # Object types
        elif field.type == FieldType.OBJECT:
            return self._map_object_type(field, struct_name_hint)

        # Conflict types
        elif field.type == FieldType.CONFLICT:
            return self._handle_type_conflict(field)

        # Unknown/fallback
        else:
            return self._get_fallback_type(field)

    def _map_array_type(self, field: Field, struct_name_hint: str) -> GoType:
        """Map array/slice types."""
        if field.array_element_type and field.array_element_type != FieldType.UNKNOWN:
            # Create a temporary field for the element type
            element_field = Field(
                name="element",
                original_name="element",
                type=field.array_element_type,
                nested_schema=field.array_element_schema,
            )

            element_type = self.map_field_type(element_field, struct_name_hint)

            return GoType(
                name=f"[]{element_type.name}",
                imports_needed=element_type.imports_needed,
                is_nilable=True,  # Slices can be nil
            )
        else:
            # Unknown element type - use interface{}
            return GoType(
                name=f"[]{self.config.unknown_type}",
                is_nilable=True,
                validation_hints=[
                    "Array with unknown element type - using interface{}"
                ],
            )

    def _map_object_type(self, field: Field, struct_name_hint: str) -> GoType:
        """Map object/struct types."""
        if field.nested_schema:
            # Use the nested schema name
            struct_name = self._generate_struct_name(
                field.nested_schema.name, struct_name_hint
            )
            return GoType(name=struct_name, is_nilable=False, is_exported=True)
        else:
            # No schema available - use interface{}
            return GoType(
                name=self.config.unknown_type,
                is_nilable=True,
                validation_hints=["Object without schema - using interface{}"],
            )

    def _handle_type_conflict(self, field: Field) -> GoType:
        """Handle fields with conflicting types."""
        if self.config.conflict_strategy == ConflictStrategy.INTERFACE:
            return GoType(
                name=self.config.unknown_type,
                is_nilable=True,
                validation_hints=[
                    f"Type conflict resolved with {self.config.unknown_type}",
                    f"Conflicting types: {[t.value for t in field.conflicting_types]}",
                ],
            )
        elif self.config.conflict_strategy == ConflictStrategy.FIRST_TYPE:
            if field.conflicting_types:
                # Use the first type in the conflict
                first_type = field.conflicting_types[0]
                temp_field = Field(name="temp", original_name="temp", type=first_type)
                result = self._map_base_type(temp_field, "")
                return result.with_validation_hint(
                    f"Used first type ({first_type.value}) from conflict: "
                    f"{[t.value for t in field.conflicting_types]}"
                )
        elif self.config.conflict_strategy == ConflictStrategy.STRICT:
            raise ValueError(
                f"Strict mode: Cannot resolve type conflict for field {field.name}. "
                f"Conflicting types: {[t.value for t in field.conflicting_types]}"
            )

        # Fallback to interface{}
        return self._get_fallback_type(field)

    def _get_fallback_type(self, field: Field) -> GoType:
        """Get fallback type for unknown situations."""
        return GoType(
            name=self.config.unknown_type,
            is_nilable=True,
            validation_hints=[
                f"Unknown field type, using fallback: {self.config.unknown_type}"
            ],
        )

    def _apply_pointer_strategy(self, base_type: GoType, field: Field) -> GoType:
        """Apply pointer strategy based on field optionality and configuration."""
        if not field.optional:
            return base_type  # Required fields don't need pointers

        strategy = self.config.pointer_strategy

        if strategy == PointerStrategy.NEVER:
            return base_type
        elif strategy == PointerStrategy.ALWAYS:
            return base_type.as_pointer()
        elif strategy == PointerStrategy.OPTIONAL_ONLY:
            # Only use pointers for optional fields of certain types
            if self._should_use_pointer_for_optional(base_type, field):
                return base_type.as_pointer()
            return base_type
        elif strategy == PointerStrategy.SMART:
            # Intelligent pointer usage
            return self._smart_pointer_decision(base_type, field)

        return base_type

    def _should_use_pointer_for_optional(self, go_type: GoType, field: Field) -> bool:
        """Determine if an optional field should use a pointer."""
        # Don't use pointers for slices, maps, or interface{} (already nilable)
        if (
            go_type.name.startswith("[]")
            or go_type.name.startswith("map[")
            or go_type.name == "interface{}"
            or go_type.name == "any"
        ):
            return False

        # Use pointers for structs and basic types when optional
        return True

    def _smart_pointer_decision(self, go_type: GoType, field: Field) -> GoType:
        """Make intelligent pointer usage decisions."""
        # This could implement more sophisticated logic
        # For now, delegate to the simpler strategy
        return (
            self._apply_pointer_strategy(go_type, field) if field.optional else go_type
        )

    def _generate_struct_name(self, schema_name: str, context_hint: str) -> str:
        """Generate appropriate struct name from schema name and context."""
        # This could be enhanced with naming conventions
        # For now, just use the schema name as-is
        return schema_name

    def _add_validation_hints(self, go_type: GoType, field: Field) -> GoType:
        """Add validation hints based on field characteristics."""
        hints = []

        # Warn about interface{} usage
        if go_type.name == "interface{}":
            hints.append(
                "Using interface{} - consider more specific typing if possible"
            )

        # Warn about potential JSON unmarshaling issues
        if field.type == FieldType.CONFLICT and "interface{}" in go_type.name:
            hints.append("Type conflict may cause JSON unmarshaling issues")

        if hints:
            return go_type.with_validation_hint("; ".join(hints))

        return go_type

    def get_all_imports(self, types: List[GoType]) -> Set[str]:
        """Extract all unique imports needed for a list of types."""
        imports = set()
        for go_type in types:
            imports.update(go_type.imports_needed)
        return imports

    def get_validation_summary(self, types: List[GoType]) -> List[str]:
        """Get all validation hints from a list of types."""
        all_hints = []
        for go_type in types:
            all_hints.extend(go_type.validation_hints)
        return all_hints


# Utility functions for creating common configurations
def create_web_api_type_config() -> GoTypeConfig:
    """Create type config optimized for web APIs."""
    return GoTypeConfig(
        int_type="int64",
        float_type="float64",
        pointer_strategy=PointerStrategy.OPTIONAL_ONLY,
        conflict_strategy=ConflictStrategy.INTERFACE,
        omit_empty_optional=True,
    )


def create_strict_type_config() -> GoTypeConfig:
    """Create type config that fails on conflicts."""
    return GoTypeConfig(
        pointer_strategy=PointerStrategy.NEVER,
        conflict_strategy=ConflictStrategy.STRICT,
    )


def create_modern_go_type_config() -> GoTypeConfig:
    """Create type config using modern Go features (1.18+)."""
    return GoTypeConfig(
        unknown_type="any",  # Use 'any' instead of interface{}
        conflict_strategy=ConflictStrategy.ANY,
    )
