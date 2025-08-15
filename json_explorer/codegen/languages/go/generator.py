"""
Go code generator implementation - Integrated with new type system.

Generates Go structs with JSON tags from JSON schema analysis.
"""

from typing import Dict, List, Optional, Any
from ...core.generator import CodeGenerator
from ...core.schema import Schema, Field
from ...core.naming import NamingCase
from .naming import create_go_sanitizer
from .types import GoTypeMapper, GoTypeConfig, GoType, PointerStrategy, ConflictStrategy
from ...core.templates import get_default_template_engine


class GoGenerator(CodeGenerator):
    """Code generator for Go structs with JSON tags."""

    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize Go generator with configuration."""
        super().__init__(config)

        # Initialize naming
        self.sanitizer = create_go_sanitizer()
        self.template_engine = get_default_template_engine()

        # Extract configuration
        self.package_name = self.config.get("package_name", "main")
        self.generate_json_tags = self.config.get("generate_json_tags", True)
        self.add_comments = self.config.get("add_comments", True)

        # Initialize type system
        self.type_config = self._build_type_config()
        self.type_mapper = GoTypeMapper(self.type_config)

        # State tracking
        self.generated_structs = set()

    def _build_type_config(self) -> GoTypeConfig:
        """Build GoTypeConfig from generator config."""
        # Map old config format to new type config
        config = self.config

        # Determine pointer strategy
        use_pointers = config.get("use_pointers_for_optional", True)
        pointer_strategy = (
            PointerStrategy.OPTIONAL_ONLY if use_pointers else PointerStrategy.NEVER
        )

        # Determine conflict strategy
        conflict_strategy = ConflictStrategy.INTERFACE  # Default safe choice

        # Create type configuration
        return GoTypeConfig(
            int_type=config.get("int_type", "int64"),
            float_type=config.get("float_type", "float64"),
            string_type=config.get("string_type", "string"),
            bool_type=config.get("bool_type", "bool"),
            time_type=config.get("time_type", "time.Time"),
            time_import=config.get("time_import", "time"),
            pointer_strategy=pointer_strategy,
            conflict_strategy=conflict_strategy,
            unknown_type=config.get("unknown_type", "interface{}"),
            omit_empty_optional=config.get("json_tag_omitempty", True),
            type_overrides=config.get("type_overrides", {}),
        )

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

        # Imports - using type system
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

        # Generate fields using new type system
        field_data_list = []
        go_types_used = []

        for field in schema.fields:
            field_data, go_type = self._generate_field_data(field, schema.name)
            if field_data:
                field_data_list.append(field_data)
                go_types_used.append(go_type)

        # Build template data
        template_data = {
            "struct_name": struct_name,
            "description": schema.description if self.add_comments else None,
            "fields": field_data_list,
        }

        # Use template if available, otherwise generate manually
        try:
            return self.template_engine.render_template("go_struct", template_data)
        except:
            # Fallback to manual generation
            return self._generate_struct_manually(template_data)

    def _generate_field_data(
        self, field: Field, schema_context: str
    ) -> tuple[Optional[Dict[str, Any]], GoType]:
        """Generate field data for template using new type system."""
        # Use type system to map the field
        go_type = self.type_mapper.map_field_type(field, schema_context)

        # Generate Go field name
        field_name = self.sanitizer.sanitize_name(field.name, NamingCase.PASCAL_CASE)

        field_data = {
            "name": field_name,
            "type": go_type.name,
            "original_name": field.original_name,
            "go_type_obj": go_type,  # Keep reference for advanced usage
        }

        # Add comment if enabled
        if self.add_comments and field.description:
            field_data["comment"] = field.description

        # Generate JSON tag
        if self.generate_json_tags:
            field_data["json_tag"] = self._generate_json_tag(field, go_type)

        return field_data, go_type

    def map_field_type(self, field: Field) -> str:
        """
        Legacy method for backwards compatibility.
        Delegates to the type system.
        """
        go_type = self.type_mapper.map_field_type(field, "")
        return go_type.name

    def _generate_json_tag(self, field: Field, go_type: GoType) -> str:
        """Generate JSON struct tag for field using type information."""
        tag_parts = [f'"{field.original_name}"']

        # Add omitempty for optional fields if configured
        if field.optional and self.type_config.omit_empty_optional:
            tag_parts.append("omitempty")

        # Add any custom JSON tag options from the type system
        if go_type.custom_json_tag:
            tag_parts.append(go_type.custom_json_tag)

        tag_content = ",".join(tag_parts)
        return f"`json:{tag_content}`"

    def get_import_statements(self, schemas: Dict[str, Schema]) -> List[str]:
        """Get required import statements using type system."""
        # Collect all types used across all schemas
        all_go_types = []

        for schema in schemas.values():
            for field in schema.fields:
                _, go_type = self._generate_field_data(field, schema.name)
                all_go_types.append(go_type)

        # Use type system to determine imports
        imports_needed = self.type_mapper.get_all_imports(all_go_types)

        if not imports_needed:
            return []

        # Format imports
        if len(imports_needed) == 1:
            return [f"import {list(imports_needed)[0]}"]

        # Multiple imports
        lines = ["import ("]
        for imp in sorted(imports_needed):
            lines.append(f"\t{imp}")
        lines.append(")")

        return lines

    def get_package_declaration(self) -> Optional[str]:
        """Get Go package declaration."""
        return f"package {self.package_name}"

    def validate_schemas(self, schemas: Dict[str, Schema]) -> List[str]:
        """Validate schemas for Go generation using type system."""
        warnings = super().validate_schemas(schemas)

        # Collect all types for validation
        all_go_types = []
        for schema in schemas.values():
            for field in schema.fields:
                _, go_type = self._generate_field_data(field, schema.name)
                all_go_types.append(go_type)

        # Get validation hints from type system
        type_warnings = self.type_mapper.get_validation_summary(all_go_types)
        warnings.extend(type_warnings)

        # Add Go-specific validations
        for schema in schemas.values():
            # Check for empty structs
            if not schema.fields:
                warnings.append(
                    f"Schema {schema.name} has no fields - will generate empty struct"
                )

            # Check for potential naming conflicts
            for field in schema.fields:
                sanitized_name = self.sanitizer.sanitize_name(
                    field.name, NamingCase.PASCAL_CASE
                )
                original_expected = field.name.title().replace("_", "").replace("-", "")
                if sanitized_name != original_expected:
                    warnings.append(
                        f"Field {schema.name}.{field.name} renamed to {sanitized_name} "
                        f"to avoid Go naming conflicts"
                    )

        # Validate package name
        if not self.package_name.isidentifier():
            warnings.append(f"Invalid Go package name: {self.package_name}")

        return warnings

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


# Factory function with type system integration
def create_go_generator(config: Optional[Dict[str, Any]] = None) -> GoGenerator:
    """Create a Go generator with default configuration."""
    default_config = {
        "package_name": "main",
        "use_pointers_for_optional": True,
        "json_tag_omitempty": True,
        "generate_json_tags": True,
        "add_comments": True,
        "int_type": "int64",
        "float_type": "float64",
        "time_type": "time.Time",
        "unknown_type": "interface{}",
    }

    merged_config = default_config.copy()
    if config:
        merged_config.update(config)

    return GoGenerator(merged_config)


# Configuration presets using type system
def create_web_api_generator() -> GoGenerator:
    """Create generator optimized for web API models."""
    return create_go_generator(
        {
            "package_name": "models",
            "use_pointers_for_optional": True,
            "json_tag_omitempty": True,
            "generate_json_tags": True,
            "add_comments": True,
            "int_type": "int64",
            "float_type": "float64",
        }
    )


def create_strict_generator() -> GoGenerator:
    """Create generator with strict type checking."""
    return create_go_generator(
        {
            "use_pointers_for_optional": False,
            "json_tag_omitempty": False,
            # This would map to ConflictStrategy.STRICT in type config
            "strict_types": True,
        }
    )


def create_modern_go_generator() -> GoGenerator:
    """Create generator using modern Go 1.18+ features."""
    return create_go_generator(
        {
            "unknown_type": "any",  # Use 'any' instead of interface{}
            "int_type": "int",  # Use plain int in modern Go
        }
    )
