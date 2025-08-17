"""
Go code generator implementation.

Generates Go structs with JSON tags using templates.
"""

from typing import Dict, List, Any
from pathlib import Path
from ...core.generator import CodeGenerator
from ...core.schema import Schema, Field, FieldType
from ...core.naming import NamingCase
from ...core.config import GeneratorConfig
from .naming import create_go_sanitizer
from .config import GoConfig


class GoGenerator(CodeGenerator):
    """Code generator for Go structs with JSON tags."""

    def __init__(self, config: GeneratorConfig):
        """Initialize Go generator with configuration."""
        super().__init__(config)

        # Initialize naming
        self.sanitizer = create_go_sanitizer()

        # Initialize Go-specific configuration
        self.go_config = GoConfig(**config.language_config)

        # State tracking
        self.generated_structs = set()
        self.types_used = set()

    @property
    def language_name(self) -> str:
        """Return the language name."""
        return "go"

    @property
    def file_extension(self) -> str:
        """Return Go file extension."""
        return ".go"

    def get_template_directory(self) -> Path:
        """Return the Go templates directory."""
        return Path(__file__).parent / "templates"

    def generate(self, schemas: Dict[str, Schema], root_schema_name: str) -> str:
        """Generate complete Go code for all schemas."""
        # Reset state
        self.generated_structs.clear()
        self.types_used.clear()
        self.sanitizer.reset_used_names()

        # Generate structs in dependency order
        generation_order = self._get_generation_order(schemas, root_schema_name)
        structs = []

        for schema_name in generation_order:
            if schema_name in schemas and schema_name not in self.generated_structs:
                struct_data = self._generate_struct_data(schemas[schema_name])
                structs.append(struct_data)
                self.generated_structs.add(schema_name)

        # Get required imports
        imports = self._get_imports()

        # Render complete file
        context = {
            "package_name": self.config.package_name,
            "imports": imports,
            "structs": structs,
        }

        return self.render_template("complete_file.go.j2", context)

    def _generate_struct_data(self, schema: Schema) -> Dict[str, Any]:
        """Generate struct data for template."""
        struct_name = self.sanitizer.sanitize_name(schema.name, NamingCase.PASCAL_CASE)

        fields = []
        for field in schema.fields:
            field_data = self._generate_field_data(field, schema.name)
            if field_data:
                fields.append(field_data)

        return {
            "struct_name": struct_name,
            "description": schema.description if self.config.add_comments else None,
            "fields": fields,
        }

    def _generate_field_data(self, field: Field, schema_context: str) -> Dict[str, Any]:
        """Generate field data for template."""
        # Generate field name
        field_name = self.sanitizer.sanitize_name(field.name, NamingCase.PASCAL_CASE)

        # Determine Go type
        go_type = self._get_field_type(field, schema_context)
        self.types_used.add(go_type)

        field_data = {
            "name": field_name,
            "type": go_type,
            "original_name": field.original_name,
        }

        # Add comment if enabled
        if self.config.add_comments and field.description:
            field_data["comment"] = field.description

        # Generate JSON tag if enabled
        if self.config.generate_json_tags:
            field_data["json_tag"] = self._generate_json_tag(field)

        return field_data

    def _get_field_type(self, field: Field, schema_context: str) -> str:
        """Get Go type for a field."""
        if field.type == FieldType.ARRAY:
            return self._get_array_type(field, schema_context)
        elif field.type == FieldType.OBJECT:
            return self._get_object_type(field, schema_context)
        else:
            return self.go_config.get_go_type(field.type, is_optional=field.optional)

    def _get_array_type(self, field: Field, schema_context: str) -> str:
        """Get Go type for array fields."""
        if field.array_element_type and field.array_element_type != FieldType.UNKNOWN:
            element_type = self.go_config.get_go_type(field.array_element_type)
        elif field.array_element_schema:
            element_name = self.sanitizer.sanitize_name(
                field.array_element_schema.name, NamingCase.PASCAL_CASE
            )
            element_type = element_name
        else:
            element_type = self.go_config.unknown_type

        return f"[]{element_type}"

    def _get_object_type(self, field: Field, schema_context: str) -> str:
        """Get Go type for object fields."""
        if field.nested_schema:
            struct_name = self.sanitizer.sanitize_name(
                field.nested_schema.name, NamingCase.PASCAL_CASE
            )

            # Add pointer for optional nested structs if configured
            if field.optional and self.go_config.use_pointers_for_optional:
                return f"*{struct_name}"
            return struct_name
        else:
            return self.go_config.unknown_type

    def _generate_json_tag(self, field: Field) -> str:
        """Generate JSON tag for field."""
        context = {
            "original_name": field.original_name,
            "optional": field.optional,
            "omitempty": self.config.json_tag_omitempty,
            "custom_options": None,
        }

        return self.render_template("json_tag.go.j2", context)

    def _get_imports(self) -> List[str]:
        """Get required imports based on types used."""
        imports = self.go_config.get_required_imports(self.types_used)
        return sorted(list(imports))

    def get_import_statements(self, schemas: Dict[str, Schema]) -> List[str]:
        """Get required import statements."""
        # This will be populated during generation
        return self._get_imports()

    def _get_generation_order(
        self, schemas: Dict[str, Schema], root_name: str
    ) -> List[str]:
        """Determine order for generating structs to handle dependencies."""
        visited = set()
        visiting = set()
        ordered = []

        def visit_schema(schema_name: str):
            if schema_name in visited or schema_name not in schemas:
                return

            if schema_name in visiting:
                return  # Circular dependency - skip

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

        return ordered

    def validate_schemas(self, schemas: Dict[str, Schema]) -> List[str]:
        """Validate schemas for Go generation."""
        warnings = super().validate_schemas(schemas)

        # Add Go-specific validations
        for schema in schemas.values():
            if not schema.fields:
                warnings.append(
                    f"Schema {schema.name} has no fields - will generate empty struct"
                )

            # Check for potential naming conflicts
            for field in schema.fields:
                sanitized = self.sanitizer.sanitize_name(
                    field.name, NamingCase.PASCAL_CASE
                )
                if sanitized != field.name.replace("_", "").replace("-", "").title():
                    warnings.append(
                        f"Field {schema.name}.{field.name} renamed to {sanitized}"
                    )

        return warnings


# Factory functions
def create_go_generator(config: GeneratorConfig = None) -> GoGenerator:
    """Create a Go generator with default configuration."""
    if config is None:
        from ...core.config import GeneratorConfig

        config = GeneratorConfig(
            package_name="main",
            generate_json_tags=True,
            json_tag_omitempty=True,
            add_comments=True,
        )

    return GoGenerator(config)


def create_web_api_generator() -> GoGenerator:
    """Create generator optimized for web API models."""
    from ...core.config import GeneratorConfig

    config = GeneratorConfig(
        package_name="models",
        generate_json_tags=True,
        json_tag_omitempty=True,
        add_comments=True,
        language_config={
            "int_type": "int64",
            "float_type": "float64",
            "use_pointers_for_optional": True,
        },
    )

    return GoGenerator(config)


def create_strict_generator() -> GoGenerator:
    """Create generator with strict types (no pointers)."""
    from ...core.config import GeneratorConfig

    config = GeneratorConfig(
        package_name="types",
        generate_json_tags=True,
        json_tag_omitempty=False,
        add_comments=True,
        language_config={"use_pointers_for_optional": False},
    )

    return GoGenerator(config)
