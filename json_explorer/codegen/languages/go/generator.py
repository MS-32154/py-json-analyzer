"""
Go code generator implementation.

Generates Go structs with JSON tags from JSON schema analysis.
"""

from typing import Dict, List, Optional, Any
from ...core.generator import CodeGenerator
from ...core.schema import Schema, Field, FieldType
from ...core.naming import NamingCase
from .naming import create_go_sanitizer
from ...core.templates import get_default_template_engine


class GoGenerator(CodeGenerator):
    """Code generator for Go structs with JSON tags."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Go generator with configuration."""
        super().__init__(config)
        self.sanitizer = create_go_sanitizer()
        self.template_engine = get_default_template_engine()

        # Load Go-specific configuration
        self.package_name = self.config.get("package_name", "main")
        self.use_pointers_for_optional = self.config.get(
            "use_pointers_for_optional", True
        )
        self.json_tag_omitempty = self.config.get("json_tag_omitempty", True)
        self.generate_json_tags = self.config.get("generate_json_tags", True)
        self.add_comments = self.config.get("add_comments", True)
        self.time_format = self.config.get("time_format", "RFC3339")
        self.int_type = self.config.get("int_type", "int64")
        self.float_type = self.config.get("float_type", "float64")

        # State tracking
        self.time_import_needed = False
        self.generated_structs = set()

    @property
    def language_name(self) -> str:
        """Return the language name."""
        return "go"

    @property
    def file_extension(self) -> str:
        """Return Go file extension."""
        return ".go"

    def generate(self, schemas: Dict[str, Schema], root_schema_name: str) -> str:
        """Generate complete Go code for all schemas."""
        # Reset state
        self.time_import_needed = False
        self.generated_structs.clear()
        self.sanitizer.reset_used_names()

        # Generate all struct definitions in dependency order
        struct_definitions = []
        generation_order = self._get_generation_order(schemas, root_schema_name)

        for schema_name in generation_order:
            if schema_name not in schemas:
                continue

            schema = schemas[schema_name]
            if schema_name not in self.generated_structs:
                struct_code = self.generate_single_schema(schema)
                if struct_code:
                    struct_definitions.append(struct_code)
                    self.generated_structs.add(schema_name)

        # Build complete file
        parts = []

        # Package declaration
        package_decl = self.get_package_declaration()
        if package_decl:
            parts.append(package_decl)
            parts.append("")  # Empty line

        # Imports
        imports = self.get_import_statements(schemas)
        if imports:
            parts.extend(imports)
            parts.append("")  # Empty line

        # Struct definitions
        parts.extend(struct_definitions)

        return "\n".join(parts)

    def generate_single_schema(self, schema: Schema) -> str:
        """Generate Go struct for a single schema."""
        struct_name = self.sanitizer.sanitize_name(schema.name, NamingCase.PASCAL_CASE)

        # Build struct using template
        template_data = {
            "struct_name": struct_name,
            "description": schema.description if self.add_comments else None,
            "fields": [],
        }

        # Generate fields
        for field in schema.fields:
            field_data = self._generate_field_data(field)
            if field_data:
                template_data["fields"].append(field_data)

        # Use template if available, otherwise generate manually
        try:
            return self.template_engine.render_template("go_struct", template_data)
        except:
            # Fallback to manual generation
            return self._generate_struct_manually(template_data)

    def _generate_struct_manually(self, data: Dict[str, Any]) -> str:
        """Manual struct generation fallback."""
        lines = []

        if data.get("description"):
            lines.append(f"// {data['description']}")

        lines.append(f"type {data['struct_name']} struct {{")

        for field in data["fields"]:
            if field.get("comment"):
                lines.append(f"\t// {field['comment']}")

            field_line = f"\t{field['name']} {field['type']}"
            if field.get("json_tag"):
                field_line += f" {field['json_tag']}"
            lines.append(field_line)

        lines.append("}")

        return "\n".join(lines)

    def _generate_field_data(self, field: Field) -> Optional[Dict[str, Any]]:
        """Generate field data for template."""
        field_name = self.sanitizer.sanitize_name(field.name, NamingCase.PASCAL_CASE)
        field_type = self.map_field_type(field)

        field_data = {
            "name": field_name,
            "type": field_type,
            "original_name": field.original_name,
        }

        # Add comment if enabled
        if self.add_comments and field.description:
            field_data["comment"] = field.description

        # Generate JSON tag
        if self.generate_json_tags:
            field_data["json_tag"] = self._generate_json_tag(field)

        return field_data

    def map_field_type(self, field: Field) -> str:
        """Map field to Go type."""
        base_type = self._get_base_go_type(field)

        # Handle optional fields with pointers
        if (
            field.optional
            and self.use_pointers_for_optional
            and self._should_use_pointer(field)
        ):
            return f"*{base_type}"

        return base_type

    def _get_base_go_type(self, field: Field) -> str:
        """Get the base Go type for a field."""
        if field.type == FieldType.STRING:
            return "string"
        elif field.type == FieldType.INTEGER:
            return self.int_type
        elif field.type == FieldType.FLOAT:
            return self.float_type
        elif field.type == FieldType.BOOLEAN:
            return "bool"
        elif field.type == FieldType.TIMESTAMP:
            self.time_import_needed = True
            return "time.Time"
        elif field.type == FieldType.OBJECT:
            if field.nested_schema:
                return self.sanitizer.sanitize_name(
                    field.nested_schema.name, NamingCase.PASCAL_CASE
                )
            return "interface{}"
        elif field.type == FieldType.ARRAY:
            element_type = self._get_array_element_type(field)
            return f"[]{element_type}"
        elif field.type == FieldType.CONFLICT:
            # For conflicts, use interface{}
            return "interface{}"
        else:
            # Unknown or other types
            return "interface{}"

    def _get_array_element_type(self, field: Field) -> str:
        """Get the Go type for array elements."""
        if field.array_element_type == FieldType.OBJECT and field.array_element_schema:
            return self.sanitizer.sanitize_name(
                field.array_element_schema.name, NamingCase.PASCAL_CASE
            )
        elif field.array_element_type:
            # Create a temporary field to get the type
            temp_field = Field(
                name="temp", original_name="temp", type=field.array_element_type
            )
            return self._get_base_go_type(temp_field)
        else:
            return "interface{}"

    def _should_use_pointer(self, field: Field) -> bool:
        """Determine if field should use pointer for optional."""
        # Don't use pointers for slices, maps, or interfaces
        if field.type in (FieldType.ARRAY, FieldType.CONFLICT, FieldType.UNKNOWN):
            return False

        # Use pointers for structs and basic types when optional
        return True

    def _generate_json_tag(self, field: Field) -> str:
        """Generate JSON struct tag for field."""
        tag_parts = [f'"{field.original_name}"']

        # Add omitempty for optional fields
        if field.optional and self.json_tag_omitempty:
            tag_parts.append("omitempty")

        tag_content = ",".join(tag_parts)
        return f'`json:"{tag_content}"`'

    def get_import_statements(self, schemas: Dict[str, Schema]) -> List[str]:
        """Get required import statements."""
        imports = []

        if self.time_import_needed:
            imports.append("import (")
            imports.append('\t"time"')
            imports.append(")")

        return imports

    def get_package_declaration(self) -> Optional[str]:
        """Get Go package declaration."""
        return f"package {self.package_name}"

    def _get_generation_order(
        self, schemas: Dict[str, Schema], root_name: str
    ) -> List[str]:
        """
        Determine order for generating structs to handle dependencies.

        Generate nested structs before structs that reference them.
        """
        visited = set()
        visiting = set()
        ordered = []

        def visit_schema(schema_name: str):
            if schema_name in visited or schema_name not in schemas:
                return

            if schema_name in visiting:
                # Circular dependency detected - skip to avoid infinite loop
                return

            visiting.add(schema_name)
            schema = schemas[schema_name]

            # Visit dependencies first
            for field in schema.fields:
                if field.nested_schema and field.nested_schema.name in schemas:
                    visit_schema(field.nested_schema.name)
                if (
                    field.array_element_schema
                    and field.array_element_schema.name in schemas
                ):
                    visit_schema(field.array_element_schema.name)

            visiting.remove(schema_name)
            visited.add(schema_name)
            ordered.append(schema_name)

        # Visit all schemas
        for schema_name in schemas:
            visit_schema(schema_name)

        # Ensure root is last if present
        if root_name in ordered:
            ordered.remove(root_name)
            ordered.append(root_name)

        return ordered

    def format_code(self, code: str) -> str:
        """Apply Go-specific formatting."""
        lines = code.split("\n")
        formatted_lines = []

        for line in lines:
            # Remove trailing whitespace
            line = line.rstrip()
            formatted_lines.append(line)

        # Remove excessive blank lines (more than 2 consecutive)
        result_lines = []
        blank_count = 0

        for line in formatted_lines:
            if not line.strip():
                blank_count += 1
                if blank_count <= 2:
                    result_lines.append(line)
            else:
                blank_count = 0
                result_lines.append(line)

        return "\n".join(result_lines)

    def validate_schemas(self, schemas: Dict[str, Schema]) -> List[str]:
        """Validate schemas for Go generation."""
        warnings = super().validate_schemas(schemas)

        # Add Go-specific validations
        for schema in schemas.values():
            # Check for empty structs
            if not schema.fields:
                warnings.append(
                    f"Schema {schema.name} has no fields - will generate empty struct"
                )

            # Check for potential JSON unmarshaling issues
            for field in schema.fields:
                if field.type == FieldType.CONFLICT:
                    warnings.append(
                        f"Field {schema.name}.{field.name} has conflicting types - "
                        f"using interface{{}} which may cause unmarshaling issues"
                    )

                # Check for reserved Go field names
                sanitized_name = self.sanitizer.sanitize_name(
                    field.name, NamingCase.PASCAL_CASE
                )
                if sanitized_name != field.name.title().replace("_", "").replace(
                    "-", ""
                ):
                    warnings.append(
                        f"Field {schema.name}.{field.name} renamed to {sanitized_name} "
                        f"to avoid Go naming conflicts"
                    )

        # Validate package name
        if not self.package_name.isidentifier():
            warnings.append(f"Invalid Go package name: {self.package_name}")

        return warnings


# Template for Go struct generation
GO_STRUCT_TEMPLATE = """
{%- if description %}
// {{ description }}
{%- endif %}
type {{ struct_name }} struct {
{%- for field in fields %}
    {%- if field.comment %}
    // {{ field.comment }}
    {%- endif %}
    {{ field.name }} {{ field.type }}{% if field.json_tag %} {{ field.json_tag }}{% endif %}
{%- endfor %}
}
"""


# Register the template
def _register_template():
    """Register Go struct template with the default engine."""
    try:
        engine = get_default_template_engine()
        engine.add_template("go_struct", GO_STRUCT_TEMPLATE)
    except:
        pass


# Register template on import
_register_template()


# Default configuration for Go generator
DEFAULT_GO_CONFIG = {
    "package_name": "main",
    "use_pointers_for_optional": True,
    "json_tag_omitempty": True,
    "generate_json_tags": True,
    "add_comments": True,
    "time_format": "RFC3339",
    "int_type": "int64",
    "float_type": "float64",
}


def create_go_generator(config: Optional[Dict[str, Any]] = None) -> GoGenerator:
    """Create a Go generator with default configuration."""
    merged_config = DEFAULT_GO_CONFIG.copy()
    if config:
        merged_config.update(config)

    return GoGenerator(merged_config)
