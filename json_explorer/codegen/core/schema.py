"""
Schema representation for code generation.

Converts analyzer output into normalized Schema/Field objects that
generators can work with consistently across languages.
"""

from dataclasses import dataclass, field
from enum import Enum
from typing import Any

from json_explorer.logging_config import get_logger

from .naming import to_pascal_case, unique_name

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
    nested_schema: Schema | None = None

    # Array information
    array_element_type: FieldType | None = None
    # Nesting depth: 1 for list[T], 2 for list[list[T]], ...
    array_dimensions: int = 1
    array_element_schema: Schema | None = None

    # Type conflicts
    conflicting_types: list[FieldType] = field(default_factory=list)

    def generate_attention_description(
        self,
        add_attention: bool = True,
    ) -> str | None:
        """Explain fields whose type falls back to interface{}/Any.

        Returns the custom description if set, otherwise a short plain-text
        note for conflicting or unknown types, or None.
        """
        if not add_attention or self.description:
            return self.description

        match self.type:
            case FieldType.CONFLICT:
                types = [t.value for t in self.conflicting_types] or ["unknown"]
                return f"Mixed types: {', '.join(types)}"
            case FieldType.UNKNOWN:
                return "Type unknown (only null values seen)"
            case FieldType.ARRAY if self.array_element_type == FieldType.CONFLICT:
                return "Array elements have mixed types"
            case FieldType.ARRAY if self.array_element_type == FieldType.UNKNOWN:
                return "Array element type unknown (empty or null-only arrays seen)"
            case _:
                return None


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
        logger.debug("Added field '%s' to schema '%s'", field.name, self.name)

    def get_field(self, name: str) -> Field | None:
        """Get field by name."""
        return next((f for f in self.fields if f.name == name), None)


# ============================================================================
# Type names
# ============================================================================

# Words whose plural form is the same or that only look plural.
_NOT_PLURAL = frozenset({"data", "news", "series", "species", "status", "info"})


def singularize(word: str) -> str:
    """Conservative English singular for naming array item types.

    ``users`` -> ``user``, ``categories`` -> ``category``,
    ``addresses`` -> ``address``, ``boxes`` -> ``box``; anything unclear
    is returned unchanged.
    """
    lower = word.lower()
    if lower in _NOT_PLURAL or len(word) < 4:
        return word
    if lower.endswith("ies"):
        return word[:-3] + "y"
    if lower.endswith(("sses", "xes", "ches", "shes", "zes")):
        return word[:-2]
    if lower.endswith("s") and not lower.endswith(("ss", "us", "is")):
        return word[:-1]
    return word


def type_name_for_key(key: str, *, item: bool = False) -> str:
    """Suggested type name for an object under ``key`` (or its array items).

    ``team_lead`` -> ``TeamLead``; items of ``projects`` -> ``Project``;
    items of ``data`` -> ``DataItem``. Uniqueness is handled later.
    """
    base = to_pascal_case(key) or "Object"
    if not item:
        return base
    singular = to_pascal_case(singularize(key))
    return singular if singular and singular != base else base + "Item"


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
    logger.info("Converting analyzer output to schema: %s", root_name)

    root_type = analyzer_result["type"]

    match root_type:
        case "object":
            # Standard case: root is an object
            schema = _create_schema_from_object(
                analyzer_result,
                root_name,
                add_attention,
            )
            logger.debug("Created object schema: %s", root_name)
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
                    "Resolved None conflict in %s.%s: using %s as optional",
                    parent_schema_name,
                    field_name,
                    concrete_types[0],
                )

            elif len(concrete_types) > 1:
                # Multiple concrete types + None → Real conflict
                # Example: [{"value": None}, {"value": 1}, {"value": "text"}]
                field_obj.type = FieldType.CONFLICT
                field_obj.conflicting_types = [
                    map_analyzer_type(t) for t in concrete_types
                ]
                field_obj.optional = True  # Can also be None
                logger.debug(
                    "Type conflict in %s.%s: %s (plus None)",
                    parent_schema_name,
                    field_name,
                    ", ".join(concrete_types),
                )

            else:
                # Only "unknown" types → Keep as unknown but mark optional
                field_obj.type = FieldType.UNKNOWN
                field_obj.optional = True
                logger.debug(
                    "Unknown type in %s.%s (only None values found)",
                    parent_schema_name,
                    field_name,
                )
        else:
            # Real conflict without None involved
            field_obj.type = FieldType.CONFLICT
            field_obj.conflicting_types = [map_analyzer_type(t) for t in conflict_types]
            logger.debug(
                "Type conflict in %s.%s: %s",
                parent_schema_name,
                field_name,
                ", ".join(conflict_types),
            )

    # Handle specific field types
    elif field_type == FieldType.OBJECT:
        nested_name = type_name_for_key(field_name)
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
                element_name = type_name_for_key(field_name, item=True)
                field_obj.array_element_schema = _create_schema_from_object(
                    child_node,
                    element_name,
                    add_attention,
                )
                field_obj.array_element_type = FieldType.OBJECT

            case "list":
                # Nested arrays: describe the innermost element and count the
                # levels, so [[1, 2]] stays list[list[int]] (not list[int])
                nested_field = _create_field_from_node(
                    child_node,
                    field_name,
                    parent_schema_name,
                    {},
                    add_attention,
                )
                field_obj.array_dimensions = nested_field.array_dimensions + 1
                field_obj.array_element_schema = nested_field.array_element_schema
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
        element_name = to_pascal_case(singularize(root_name)) or root_name
        schema = _create_schema_from_object(child_node, element_name, add_attention)

        logger.info(
            "Root is array of objects, extracted element schema: %s", element_name
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

    schema.add_field(field_obj)
    logger.info("Root is array of primitives: %s", element_type.value)
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

    schema.add_field(field_obj)
    logger.info("Root is primitive: %s", root_type)
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
    seen: set[int] = set()

    def collect(schema: Schema) -> None:
        if id(schema) in seen:
            return
        seen.add(id(schema))
        # Different objects can suggest the same name (two "address" keys at
        # different paths): number them instead of dropping one.
        schema.name = unique_name(schema.name, set(schemas))
        schemas[schema.name] = schema
        for fld in schema.fields:
            if fld.nested_schema:
                collect(fld.nested_schema)
            if fld.array_element_schema:
                collect(fld.array_element_schema)

    collect(root_schema)
    logger.info("Extracted %s schemas from root: %s", len(schemas), root_schema.name)
    return schemas
