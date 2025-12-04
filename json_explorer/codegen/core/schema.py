"""
Schema representation for code generation.

Converts analyzer output into normalized Schema/Field objects that
generators can work with consistently across languages.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Field Types
# ============================================================================


class FieldType(Enum):
    """Supported field types across all target languages."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    TIMESTAMP = "timestamp"
    OBJECT = "object"
    ARRAY = "array"
    UNKNOWN = "unknown"
    CONFLICT = "conflict"  # Multiple types detected


# Analyzer type to FieldType mapping
ANALYZER_TYPE_MAP: dict[str, FieldType] = {
    "str": FieldType.STRING,
    "int": FieldType.INTEGER,
    "float": FieldType.FLOAT,
    "bool": FieldType.BOOLEAN,
    "timestamp": FieldType.TIMESTAMP,
    "object": FieldType.OBJECT,
    "list": FieldType.ARRAY,
    "conflict": FieldType.CONFLICT,
    "unknown": FieldType.UNKNOWN,
}


def map_analyzer_type(analyzer_type: str) -> FieldType:
    """Map analyzer type string to FieldType enum."""
    return ANALYZER_TYPE_MAP.get(analyzer_type, FieldType.UNKNOWN)


# ============================================================================
# Schema Data Structures
# ============================================================================


@dataclass(slots=True)
class Field:
    """
    Represents a single field in a data structure.

    Attributes:
        name: Sanitized field name
        original_name: Original JSON key (preserved for tags/annotations)
        type: Field type
        optional: Whether field can be absent
        description: Auto-generated or custom description
        nested_schema: For OBJECT types
        array_element_type: For ARRAY of primitives
        array_element_schema: For ARRAY of objects
        conflicting_types: Types involved in conflicts
    """

    name: str
    original_name: str
    type: FieldType
    optional: bool = False
    description: str | None = None

    # Nested structures
    nested_schema: "Schema | None" = None

    # Array information
    array_element_type: FieldType | None = None
    array_element_schema: "Schema | None" = None

    # Type conflicts
    conflicting_types: list[FieldType] = field(default_factory=list)

    def is_complex(self) -> bool:
        """Check if field contains complex nested structures."""
        if self.type == FieldType.OBJECT:
            return self.nested_schema is not None
        if self.type == FieldType.ARRAY:
            return self.array_element_schema is not None
        return False

    def generate_attention_description(
        self,
        add_attention: bool = True,
    ) -> str | None:
        """
        Generate warning description for special cases.

        Returns None for normal fields, description string for problematic ones.
        """
        if not add_attention or self.description:
            return self.description

        # Pattern match on field type
        match self.type:
            case FieldType.CONFLICT:
                types = (
                    [t.value for t in self.conflicting_types]
                    if self.conflicting_types
                    else ["unknown"]
                )
                return f"⚠️ Mixed types: {', '.join(types)}"

            case FieldType.UNKNOWN:
                return "❓ Type unknown"

            case FieldType.ARRAY if self.array_element_type == FieldType.CONFLICT:
                return "📋 Array with mixed types"

            case FieldType.ARRAY if self.array_element_type == FieldType.UNKNOWN:
                return "📋 Array with unknown element type"

            case FieldType.ARRAY if (
                self.array_element_schema and self._is_complex_array()
            ):
                return "📋 Array of complex objects"

            case FieldType.OBJECT if (
                self.optional and self.nested_schema and self._is_complex_nested()
            ):
                return "🔗 Optional complex structure"

            case _:
                return None

    def _is_complex_array(self) -> bool:
        """Check if array contains complex nested structures."""
        return bool(
            self.array_element_schema and len(self.array_element_schema.fields) > 5
        )

    def _is_complex_nested(self) -> bool:
        """Check if nested object is complex."""
        if not self.nested_schema:
            return False
        return len(self.nested_schema.fields) > 3 or self._has_deep_nesting()

    def _has_deep_nesting(self) -> bool:
        """Check if nested structure has deep nesting."""
        if not self.nested_schema:
            return False

        for field in self.nested_schema.fields:
            if field.type in (FieldType.OBJECT, FieldType.ARRAY):
                if field.nested_schema or field.array_element_schema:
                    return True
        return False


@dataclass(slots=True)
class Schema:
    """
    Represents the structure of a data object.

    Attributes:
        name: Schema name (sanitized)
        original_name: Original name from JSON
        fields: List of fields in this schema
        description: Optional description
    """

    name: str
    original_name: str
    fields: list[Field] = field(default_factory=list)
    description: str | None = None

    def add_field(self, field: Field) -> None:
        """Add a field to this schema."""
        self.fields.append(field)
        logger.debug(f"Added field '{field.name}' to schema '{self.name}'")

    def get_field(self, name: str) -> Field | None:
        """Get field by name."""
        return next((f for f in self.fields if f.name == name), None)

    def get_max_depth(self, current_depth: int = 1) -> int:
        """Calculate maximum nesting depth."""
        max_depth = current_depth

        for field in self.fields:
            if field.nested_schema:
                depth = field.nested_schema.get_max_depth(current_depth + 1)
                max_depth = max(max_depth, depth)
            elif field.array_element_schema:
                depth = field.array_element_schema.get_max_depth(current_depth + 1)
                max_depth = max(max_depth, depth)

        return max_depth

    def generate_attention_description(
        self,
        add_attention: bool = True,
    ) -> str | None:
        """Generate warning description for special schema cases."""
        if not add_attention or self.description:
            return self.description

        # Empty schemas
        if not self.fields:
            return "⚠️ No fields detected"

        # Count issues
        conflicts = sum(1 for f in self.fields if f.type == FieldType.CONFLICT)
        unknowns = sum(1 for f in self.fields if f.type == FieldType.UNKNOWN)

        # Multiple issues
        if conflicts >= 3:
            return f"⚠️ Multiple type conflicts ({conflicts} fields)"
        if unknowns >= 3:
            return f"❓ Multiple unknown types ({unknowns} fields)"
        if conflicts > 0 and unknowns > 0:
            return f"⚠️ Mixed issues: {conflicts} conflicts, {unknowns} unknowns"

        # Large or deeply nested
        if len(self.fields) >= 15:
            return f"📊 Large structure ({len(self.fields)} fields)"
        if self.get_max_depth() >= 3:
            return "🗂️ Deeply nested structure"

        return None

    def get_statistics(self) -> dict[str, int]:
        """Get schema statistics."""
        return {
            "total_fields": len(self.fields),
            "conflicts": sum(1 for f in self.fields if f.type == FieldType.CONFLICT),
            "unknowns": sum(1 for f in self.fields if f.type == FieldType.UNKNOWN),
            "optional_fields": sum(1 for f in self.fields if f.optional),
            "complex_arrays": sum(
                1
                for f in self.fields
                if f.type == FieldType.ARRAY and f.array_element_schema
            ),
            "max_depth": self.get_max_depth(),
        }


# ============================================================================
# Analyzer Output Conversion
# ============================================================================


def convert_analyzer_output(
    analyzer_result: dict[str, Any],
    root_name: str = "Root",
    add_attention: bool = True,
) -> Schema:
    """
    Convert analyzer output to internal Schema representation.

    Args:
        analyzer_result: Output from analyze_json()
        root_name: Name for root schema
        add_attention: Generate attention descriptions for issues

    Returns:
        Root Schema object with nested structures
    """
    logger.info(f"Converting analyzer output to schema: {root_name}")

    root_type = analyzer_result["type"]

    match root_type:
        case "object":
            # Standard case: root is an object
            schema = _create_schema_from_object(
                analyzer_result,
                root_name,
                add_attention,
            )
            logger.debug(f"Created object schema: {root_name}")
            return schema

        case "list":
            # Root is an array
            return _handle_root_array(analyzer_result, root_name, add_attention)

        case _:
            # Root is a primitive value
            return _handle_root_primitive(
                analyzer_result, root_name, root_type, add_attention
            )


def _create_schema_from_object(
    node: dict[str, Any],
    schema_name: str,
    add_attention: bool,
) -> Schema:
    """Create schema from analyzer object node."""
    schema = Schema(name=schema_name, original_name=schema_name)

    children = node.get("children", {})
    conflicts = node.get("conflicts", {})

    for field_name, field_data in children.items():
        field_obj = _create_field_from_node(
            field_data,
            field_name,
            schema_name,
            conflicts,
            add_attention,
        )
        schema.add_field(field_obj)

    # Generate attention description
    if add_attention:
        desc = schema.generate_attention_description(True)
        if desc:
            schema.description = desc

    return schema


def _create_field_from_node(
    field_node: dict[str, Any],
    field_name: str,
    parent_schema_name: str,
    conflicts: dict[str, Any],
    add_attention: bool,
) -> Field:
    """Create field from analyzer field node."""
    field_type_str = field_node["type"]
    field_type = map_analyzer_type(field_type_str)
    optional = field_node.get("optional", False)

    field_obj = Field(
        name=field_name,
        original_name=field_name,
        type=field_type,
        optional=optional,
    )

    # Handle type conflicts with None/unknown handling
    if field_name in conflicts:
        conflict_types = conflicts[field_name]

        if "unknown" in conflict_types:
            # Filter out "unknown" to see what concrete types remain
            concrete_types = [t for t in conflict_types if t != "unknown"]

            if len(concrete_types) == 1:
                # Single concrete type + None → Optional[ConcreteType]
                # This is the most common case and should NOT be treated as a conflict
                field_obj.type = map_analyzer_type(concrete_types[0])
                field_obj.optional = True
                logger.debug(
                    f"Resolved None conflict in {parent_schema_name}.{field_name}: "
                    f"using {concrete_types[0]} as optional"
                )

            elif len(concrete_types) > 1:
                # Multiple concrete types + None → Real conflict
                # Example: [{"value": None}, {"value": 1}, {"value": "text"}]
                field_obj.type = FieldType.CONFLICT
                field_obj.conflicting_types = [
                    map_analyzer_type(t) for t in concrete_types
                ]
                field_obj.optional = True  # Can also be None
                logger.warning(
                    f"Type conflict in {parent_schema_name}.{field_name}: "
                    f"{', '.join(concrete_types)} (plus None)"
                )

            else:
                # Only "unknown" types → Keep as unknown but mark optional
                field_obj.type = FieldType.UNKNOWN
                field_obj.optional = True
                logger.debug(
                    f"Unknown type in {parent_schema_name}.{field_name} "
                    f"(only None values found)"
                )
        else:
            # Real conflict without None involved
            field_obj.type = FieldType.CONFLICT
            field_obj.conflicting_types = [map_analyzer_type(t) for t in conflict_types]
            logger.warning(
                f"Type conflict in {parent_schema_name}.{field_name}: "
                f"{', '.join(conflict_types)}"
            )

    # Handle specific field types
    elif field_type == FieldType.OBJECT:
        nested_name = f"{parent_schema_name}{field_name.title()}"
        field_obj.nested_schema = _create_schema_from_object(
            field_node,
            nested_name,
            add_attention,
        )

    elif field_type == FieldType.ARRAY:
        _handle_array_field(
            field_obj, field_node, parent_schema_name, field_name, add_attention
        )

    # Generate attention description
    if add_attention:
        desc = field_obj.generate_attention_description(True)
        if desc:
            field_obj.description = desc

    return field_obj


def _handle_array_field(
    field_obj: Field,
    field_node: dict[str, Any],
    parent_schema_name: str,
    field_name: str,
    add_attention: bool,
) -> None:
    """Handle array field type detection."""
    if "child_type" in field_node:
        # Simple array (primitives or mixed)
        child_type_str = field_node["child_type"]
        if "mixed" in child_type_str.lower():
            field_obj.array_element_type = FieldType.CONFLICT
        else:
            field_obj.array_element_type = map_analyzer_type(child_type_str)

    elif "child" in field_node:
        # Complex array (objects or nested arrays)
        child_node = field_node["child"]
        child_type = child_node["type"]

        match child_type:
            case "object":
                # Array of objects
                element_name = f"{parent_schema_name}{field_name.title()}Item"
                field_obj.array_element_schema = _create_schema_from_object(
                    child_node,
                    element_name,
                    add_attention,
                )
                field_obj.array_element_type = FieldType.OBJECT

            case "list":
                # Nested arrays
                field_obj.array_element_type = FieldType.ARRAY
                # Recursively handle nested arrays
                nested_field = _create_field_from_node(
                    child_node,
                    f"{field_name}_item",
                    parent_schema_name,
                    {},
                    add_attention,
                )
                if nested_field.array_element_schema:
                    field_obj.array_element_schema = nested_field.array_element_schema
                else:
                    field_obj.array_element_type = nested_field.array_element_type

            case _:
                # Other types
                field_obj.array_element_type = map_analyzer_type(child_type)

    else:
        # Unknown array type
        field_obj.array_element_type = FieldType.UNKNOWN


def _handle_root_array(
    analyzer_result: dict[str, Any],
    root_name: str,
    add_attention: bool,
) -> Schema:
    """Handle case where root is an array."""
    if "child" in analyzer_result and analyzer_result["child"]["type"] == "object":
        # Array of objects - use element schema as root
        child_node = analyzer_result["child"]
        element_name = (
            root_name.rstrip("s") if root_name.endswith("s") else f"{root_name}Item"
        )
        schema = _create_schema_from_object(child_node, element_name, add_attention)

        if add_attention:
            prefix = "◉ Generated from array of objects"
            schema.description = (
                f"{prefix}\n{schema.description}" if schema.description else prefix
            )

        logger.info(
            f"Root is array of objects, extracted element schema: {element_name}"
        )
        return schema

    # Array of primitives or unknown - create wrapper
    schema = Schema(name=root_name, original_name=root_name)

    if "child_type" in analyzer_result:
        child_type_str = analyzer_result["child_type"]
        element_type = (
            FieldType.CONFLICT
            if "mixed" in child_type_str.lower()
            else map_analyzer_type(child_type_str)
        )
    else:
        element_type = FieldType.UNKNOWN

    field_obj = Field(
        name="items",
        original_name="items",
        type=FieldType.ARRAY,
        array_element_type=element_type,
    )

    if add_attention:
        field_obj.description = f"📋 Array of {element_type.value} values"

    schema.add_field(field_obj)
    logger.info(f"Root is array of primitives: {element_type.value}")
    return schema


def _handle_root_primitive(
    analyzer_result: dict[str, Any],
    root_name: str,
    root_type: str,
    add_attention: bool,
) -> Schema:
    """Handle case where root is a primitive value."""
    schema = Schema(name=root_name, original_name=root_name)
    field_obj = Field(
        name="value",
        original_name="value",
        type=map_analyzer_type(root_type),
    )

    if add_attention:
        field_obj.description = f"📦 Single {root_type} value"

    schema.add_field(field_obj)
    logger.info(f"Root is primitive: {root_type}")
    return schema


# ============================================================================
# Schema Extraction
# ============================================================================


def extract_all_schemas(root_schema: Schema) -> dict[str, Schema]:
    """
    Extract all nested schemas into flat dictionary.

    Args:
        root_schema: Root schema with potential nested schemas

    Returns:
        Dictionary mapping schema names to Schema objects
    """
    schemas: dict[str, Schema] = {}

    def collect(schema: Schema) -> None:
        schemas[schema.name] = schema
        for field in schema.fields:
            if field.nested_schema:
                collect(field.nested_schema)
            if field.array_element_schema:
                collect(field.array_element_schema)

    collect(root_schema)
    logger.info(f"Extracted {len(schemas)} schemas from root: {root_schema.name}")
    return schemas
