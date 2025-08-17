"""
Core schema representation for code generation.

Converts analyzer.py output into a normalized internal format
that generators can work with consistently.
"""

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Union, Any
from enum import Enum


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
    CONFLICT = "conflict"  # When multiple types detected


@dataclass
class Field:
    """Represents a single field in a data structure."""

    name: str
    original_name: str  # Keep original JSON key for tags/annotations
    type: FieldType
    optional: bool = False
    description: Optional[str] = None

    # For nested objects
    nested_schema: Optional["Schema"] = None

    # For arrays
    array_element_type: Optional[FieldType] = None
    array_element_schema: Optional["Schema"] = None

    # Type conflicts (when field has inconsistent types)
    conflicting_types: List[FieldType] = field(default_factory=list)

    def generate_attention_description(
        self, add_attention_descriptions: bool = True
    ) -> Optional[str]:
        """
        Generate attention-making description for special cases.

        Args:
            add_attention_descriptions: Whether to generate attention descriptions

        Returns:
            Description string for special cases, None for normal fields
        """
        if not add_attention_descriptions:
            return None

        # Don't override existing descriptions
        if self.description:
            return self.description

        # Type conflicts - highest priority
        if self.type == FieldType.CONFLICT:
            if self.conflicting_types:
                type_names = [t.value for t in self.conflicting_types]
                return f"⚠️ Mixed types: {', '.join(type_names)}"
            return "⚠️ Mixed types detected"

        # Unknown types
        if self.type == FieldType.UNKNOWN:
            return "❓ Type unknown"

        # Complex arrays
        if self.type == FieldType.ARRAY:
            if self.array_element_type == FieldType.CONFLICT:
                return "📋 Array with mixed types"
            elif self.array_element_type == FieldType.UNKNOWN:
                return "📋 Array with unknown element type"
            elif self.array_element_schema and self._is_complex_array():
                return "📋 Array of complex objects"

        # Optional nested objects
        if self.type == FieldType.OBJECT and self.optional and self.nested_schema:
            if self._is_complex_nested():
                return "🔗 Optional complex structure"

        # Normal fields get no auto-generated description
        return None

    def _is_complex_array(self) -> bool:
        """Check if array contains complex nested structures."""
        if not self.array_element_schema:
            return False
        return len(self.array_element_schema.fields) > 5

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
            if field.type == FieldType.OBJECT and field.nested_schema:
                return True
            if field.type == FieldType.ARRAY and field.array_element_schema:
                return True
        return False


@dataclass
class Schema:
    """Represents the structure of a data object."""

    name: str
    original_name: str
    fields: List[Field] = field(default_factory=list)
    description: Optional[str] = None

    def add_field(self, field: Field) -> None:
        """Add a field to this schema."""
        self.fields.append(field)

    def get_field(self, name: str) -> Optional[Field]:
        """Get field by name."""
        for field in self.fields:
            if field.name == name:
                return field
        return None

    def generate_attention_description(
        self, add_attention_descriptions: bool = True
    ) -> Optional[str]:
        """
        Generate attention-making description for special schema cases.

        Args:
            add_attention_descriptions: Whether to generate attention descriptions

        Returns:
            Description string for special cases, None for normal schemas
        """
        if not add_attention_descriptions:
            return None

        # Don't override existing descriptions
        if self.description:
            return self.description

        # Empty schemas
        if not self.fields:
            return "⚠️ No fields detected"

        # Count special field types
        conflict_count = sum(1 for f in self.fields if f.type == FieldType.CONFLICT)
        unknown_count = sum(1 for f in self.fields if f.type == FieldType.UNKNOWN)

        # Many conflicts
        if conflict_count >= 3:
            return f"⚠️ Multiple type conflicts ({conflict_count} fields)"

        # Many unknowns
        if unknown_count >= 3:
            return f"❓ Multiple unknown types ({unknown_count} fields)"

        # Large schemas
        if len(self.fields) >= 15:
            return f"📊 Large structure ({len(self.fields)} fields)"

        # Deep nesting
        if self._has_deep_nesting():
            return "🏗️ Deeply nested structure"

        # Mixed issues
        if conflict_count > 0 and unknown_count > 0:
            return (
                f"⚠️ Mixed issues: {conflict_count} conflicts, {unknown_count} unknowns"
            )

        # Normal schemas get no auto-generated description
        return None

    def _has_deep_nesting(self) -> bool:
        """Check if schema has deep nesting (3+ levels)."""
        return self._get_max_depth() >= 3

    def _get_max_depth(self, current_depth: int = 1) -> int:
        """Get maximum nesting depth of this schema."""
        max_depth = current_depth

        for field in self.fields:
            if field.type == FieldType.OBJECT and field.nested_schema:
                depth = field.nested_schema._get_max_depth(current_depth + 1)
                max_depth = max(max_depth, depth)
            elif field.type == FieldType.ARRAY and field.array_element_schema:
                depth = field.array_element_schema._get_max_depth(current_depth + 1)
                max_depth = max(max_depth, depth)

        return max_depth

    def get_attention_summary(self) -> Dict[str, int]:
        """Get summary of attention-worthy issues in this schema."""
        summary = {
            "conflicts": 0,
            "unknowns": 0,
            "empty_schemas": 0,
            "complex_arrays": 0,
            "max_depth": 1,
            "total_fields": len(self.fields),
        }

        # Count field-level issues
        for field in self.fields:
            if field.type == FieldType.CONFLICT:
                summary["conflicts"] += 1
            elif field.type == FieldType.UNKNOWN:
                summary["unknowns"] += 1
            elif field.type == FieldType.ARRAY and field._is_complex_array():
                summary["complex_arrays"] += 1

        # Schema-level metrics
        summary["max_depth"] = self._get_max_depth()

        return summary


def convert_analyzer_output(
    analyzer_result: Dict[str, Any],
    root_name: str = "Root",
    add_attention_descriptions: bool = True,
) -> Schema:
    """
    Convert analyzer.py output to internal Schema representation.

    Args:
        analyzer_result: Output from analyze_json() function
        root_name: Name for the root schema object
        add_attention_descriptions: Whether to generate attention descriptions

    Returns:
        Schema: Normalized schema representation with attention descriptions
    """

    def map_analyzer_type(analyzer_type: str) -> FieldType:
        """Map analyzer types to our FieldType enum."""
        type_mapping = {
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
        return type_mapping.get(analyzer_type, FieldType.UNKNOWN)

    def convert_node(node: Dict[str, Any], name: str) -> Schema:
        """Recursively convert analyzer node to Schema."""
        schema = Schema(name=name, original_name=name)

        if node["type"] != "object":
            raise ValueError(f"Expected object type, got {node['type']}")

        children = node.get("children", {})
        conflicts = node.get("conflicts", {})

        for field_name, field_data in children.items():
            field_type = map_analyzer_type(field_data["type"])
            optional = field_data.get("optional", False)

            field_obj = Field(
                name=field_name,
                original_name=field_name,
                type=field_type,
                optional=optional,
            )

            # Handle conflicts
            if field_name in conflicts:
                field_obj.type = FieldType.CONFLICT
                field_obj.conflicting_types = [
                    map_analyzer_type(t) for t in conflicts[field_name]
                ]

            # Handle nested objects
            elif field_type == FieldType.OBJECT:
                nested_name = f"{name}{field_name.title()}"
                field_obj.nested_schema = convert_node(field_data, nested_name)

            # Handle arrays
            elif field_type == FieldType.ARRAY:
                if "child_type" in field_data:
                    # Simple array (primitives)
                    child_type_str = field_data["child_type"]
                    if "mixed" in child_type_str.lower():
                        field_obj.array_element_type = FieldType.CONFLICT
                    else:
                        field_obj.array_element_type = map_analyzer_type(child_type_str)
                elif "child" in field_data:
                    # Complex array (objects/nested arrays)
                    child_data = field_data["child"]
                    if child_data["type"] == "object":
                        nested_name = f"{name}{field_name.title()}Item"
                        field_obj.array_element_schema = convert_node(
                            child_data, nested_name
                        )
                        field_obj.array_element_type = FieldType.OBJECT
                    else:
                        field_obj.array_element_type = map_analyzer_type(
                            child_data["type"]
                        )

            # Generate attention description for field
            if add_attention_descriptions:
                attention_desc = field_obj.generate_attention_description(True)
                if attention_desc:
                    field_obj.description = attention_desc

            schema.add_field(field_obj)

        # Generate attention description for schema
        if add_attention_descriptions:
            attention_desc = schema.generate_attention_description(True)
            if attention_desc:
                schema.description = attention_desc

        return schema

    # Convert root level
    if analyzer_result["type"] == "object":
        return convert_node(analyzer_result, root_name)
    else:
        # Handle case where root is not an object
        schema = Schema(name=root_name, original_name=root_name)
        root_field = Field(
            name="value",
            original_name="value",
            type=map_analyzer_type(analyzer_result["type"]),
        )

        # Generate attention description for primitive root
        if add_attention_descriptions:
            attention_desc = root_field.generate_attention_description(True)
            if attention_desc:
                root_field.description = attention_desc

        schema.add_field(root_field)
        return schema


def extract_all_schemas(root_schema: Schema) -> Dict[str, Schema]:
    """
    Extract all nested schemas into a flat dictionary.

    Returns:
        Dict mapping schema name to Schema object
    """
    schemas = {}

    def collect_schemas(schema: Schema):
        schemas[schema.name] = schema

        for field in schema.fields:
            if field.nested_schema:
                collect_schemas(field.nested_schema)
            if field.array_element_schema:
                collect_schemas(field.array_element_schema)

    collect_schemas(root_schema)
    return schemas
