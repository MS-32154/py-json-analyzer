"""
Schema representation for code generation.

Converts analyzer output into normalized Schema/Field objects that
generators can work with consistently across languages.
"""

from dataclasses import dataclass, field, replace
from enum import StrEnum

from json_explorer.analyzer import Format, Kind, Node
from json_explorer.logging_config import get_logger

from .naming import to_pascal_case, unique_name

logger = get_logger(__name__)


# ============================================================================
# Field Types
# ============================================================================


class FieldType(StrEnum):
    """Field types shared by all target languages."""

    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    # Strings in a standard format (RFC 3339 / JSON Schema "format")
    DATE_TIME = "date-time"
    LOCAL_DATE_TIME = "local-date-time"
    DATE = "date"
    TIME = "time"
    DURATION = "duration"
    OBJECT = "object"
    ARRAY = "array"
    UNKNOWN = "unknown"  # only null values (or empty arrays) seen
    CONFLICT = "conflict"  # different kinds seen


_KIND_TYPES: dict[Kind, FieldType] = {
    Kind.STRING: FieldType.STRING,
    Kind.INTEGER: FieldType.INTEGER,
    Kind.FLOAT: FieldType.FLOAT,
    Kind.BOOLEAN: FieldType.BOOLEAN,
    Kind.OBJECT: FieldType.OBJECT,
    Kind.ARRAY: FieldType.ARRAY,
    Kind.NULL: FieldType.UNKNOWN,
    Kind.MIXED: FieldType.CONFLICT,
}
_FORMAT_TYPES: dict[Format, FieldType] = {
    Format.DATE_TIME: FieldType.DATE_TIME,
    Format.LOCAL_DATE_TIME: FieldType.LOCAL_DATE_TIME,
    Format.DATE: FieldType.DATE,
    Format.TIME: FieldType.TIME,
    Format.DURATION: FieldType.DURATION,
}


def field_type_of(node: Node | None) -> FieldType:
    """FieldType for an analyzer node (``None``: nothing seen)."""
    if node is None:
        return FieldType.UNKNOWN
    if node.kind == Kind.STRING and node.format:
        return _FORMAT_TYPES[node.format]
    return _KIND_TYPES[node.kind]


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
    analysis: Node,
    root_name: str = "Root",
    add_attention: bool = True,
) -> Schema:
    """Turn ``analyze_json()`` output into a root Schema with nested schemas.

    The root is the analyzed object; for an array of objects, the element
    type (named after ``root_name``); otherwise a wrapper with one field
    (``items`` for other arrays, ``value`` for a single value).
    """
    match analysis:
        case Node(kind=Kind.OBJECT):
            return _schema(analysis, root_name, add_attention)
        case Node(kind=Kind.ARRAY, items=Node(kind=Kind.OBJECT) as element):
            name = to_pascal_case(singularize(root_name)) or root_name
            return _schema(element, name, add_attention)
        case Node(kind=Kind.ARRAY):
            wrapper_key = "items"
        case _:
            wrapper_key = "value"
    schema = Schema(name=root_name, original_name=root_name)
    schema.add_field(
        _field(wrapper_key, replace(analysis, optional=False), add_attention)
    )
    return schema


def _schema(node: Node, name: str, add_attention: bool) -> Schema:
    schema = Schema(name=name, original_name=name)
    for key, child in node.fields.items():
        schema.add_field(_field(key, child, add_attention))
    return schema


def _field(key: str, node: Node, add_attention: bool) -> Field:
    fld = Field(
        name=key, original_name=key, type=field_type_of(node), optional=node.optional
    )
    match node.kind:
        case Kind.MIXED:
            fld.conflicting_types = sorted({_KIND_TYPES[k] for k in node.kinds})
        case Kind.OBJECT:
            fld.nested_schema = _schema(node, type_name_for_key(key), add_attention)
        case Kind.ARRAY:
            # Nested arrays: describe the innermost element and count levels
            element, dimensions = node.items, 1
            while element is not None and element.kind == Kind.ARRAY:
                element, dimensions = element.items, dimensions + 1
            fld.array_dimensions = dimensions
            fld.array_element_type = field_type_of(element)
            if element is not None and element.kind == Kind.OBJECT:
                name = type_name_for_key(key, item=True)
                fld.array_element_schema = _schema(element, name, add_attention)
    if add_attention:
        fld.description = fld.generate_attention_description(True)
    return fld


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
