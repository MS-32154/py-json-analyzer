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
    nested_schema: Optional['Schema'] = None
    
    # For arrays
    array_element_type: Optional[FieldType] = None
    array_element_schema: Optional['Schema'] = None
    
    # Type conflicts (when field has inconsistent types)
    conflicting_types: List[FieldType] = field(default_factory=list)


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


def convert_analyzer_output(analyzer_result: Dict[str, Any], root_name: str = "Root") -> Schema:
    """
    Convert analyzer.py output to internal Schema representation.
    
    Args:
        analyzer_result: Output from analyze_json() function
        root_name: Name for the root schema object
    
    Returns:
        Schema: Normalized schema representation
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
                optional=optional
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
                        field_obj.array_element_schema = convert_node(child_data, nested_name)
                        field_obj.array_element_type = FieldType.OBJECT
                    else:
                        field_obj.array_element_type = map_analyzer_type(child_data["type"])
            
            schema.add_field(field_obj)
        
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
            type=map_analyzer_type(analyzer_result["type"])
        )
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
