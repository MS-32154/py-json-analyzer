"""
Go code generator implementation.

Generates Go structs with JSON tags using templates.
"""

import json
from pathlib import Path
from typing import Any

from json_explorer.logging_config import get_logger

from ...core.config import GeneratorConfig
from ...core.generator import CodeGenerator
from ...core.naming import NamePlan, plan_names
from ...core.schema import Field, FieldType, Schema
from .config import UNKNOWN_TYPE, GoConfig
from .naming import go_identifier, go_json_tag, is_valid_json_tag_name

logger = get_logger(__name__)


# ============================================================================
# Go Code Generator
# ============================================================================


class GoGenerator(CodeGenerator):
    """Code generator for Go structs with JSON tags."""

    __slots__ = ("_names", "go_config", "types_used")

    def __init__(self, config: GeneratorConfig):
        """Initialize Go generator with configuration."""
        # Initialize Go-specific config from language_config
        self.go_config = GoConfig(**config.language_config)

        # Identifiers for the current run (see generate())
        self._names: NamePlan | None = None

        # Track types for imports
        self.types_used: set[str] = set()

        # Call parent init (sets up templates)
        super().__init__(config)

        logger.info("GoGenerator initialized")

    # ========================================================================
    # Required Properties
    # ========================================================================

    @property
    def language_name(self) -> str:
        """Return language name."""
        return "go"

    @property
    def file_extension(self) -> str:
        """Return Go file extension."""
        return ".go"

    def get_template_directory(self) -> Path:
        """Return Go templates directory."""
        return Path(__file__).parent / "templates"

    # ========================================================================
    # Code Generation
    # ========================================================================

    def generate(
        self,
        schemas: dict[str, Schema],
        root_schema_name: str,
    ) -> str:
        """Generate complete Go code for all schemas."""
        logger.info("Generating Go code for %s schemas", len(schemas))

        # Reset state; name every type and field once, before rendering
        self.types_used.clear()
        self._names = plan_names(
            schemas.values(),
            type_identifier=lambda name: go_identifier(name, fallback="Type"),
            field_identifier=go_identifier,
        )

        # Generate structs in dependency order
        generation_order = self._get_generation_order(schemas, root_schema_name)
        structs = []

        for schema_name in generation_order:
            if schema_name in schemas:
                struct_data = self._generate_struct_data(schemas[schema_name])
                structs.append(struct_data)

        logger.debug("Generated %s structs", len(structs))

        # Get required imports
        imports = self._get_imports()

        # Render complete file
        context = {
            "package_name": self.config.package_name,
            "imports": imports,
            "structs": structs,
        }

        return self.render_template("complete_file.go.j2", context)

    def _generate_struct_data(self, schema: Schema) -> dict[str, Any]:
        """Generate struct data for template."""
        struct_name = self.names.type_name(schema)

        fields = []
        for field in schema.fields:
            field_data = self._generate_field_data(field)
            if field_data:
                fields.append(field_data)

        logger.debug("Generated struct: %s with %s fields", struct_name, len(fields))

        return {
            "struct_name": struct_name,
            "description": schema.description if self.config.add_comments else None,
            "fields": fields,
        }

    def _generate_field_data(self, field: Field) -> dict[str, Any]:
        """Generate field data for template."""
        field_name = self.names.field_name(field)

        # encoding/json can't map keys like `a,b` or `q"k` with a tag: leave
        # the field out (with a note) rather than map it to the wrong key.
        if not is_valid_json_tag_name(field.original_name):
            return {
                "skipped": (
                    f"JSON key {json.dumps(field.original_name, ensure_ascii=False)}"
                    " can't be expressed as a Go struct tag; field omitted"
                )
            }

        # Determine Go type
        go_type = self._get_field_type(field)
        self.types_used.add(go_type)

        field_data = {
            "name": field_name,
            "type": go_type,
            "original_name": field.original_name,
        }

        # Add comment if enabled
        if self.config.add_comments and field.description:
            field_data["comment"] = field.description

        field_data["json_tag"] = self._generate_json_tag(field)

        return field_data

    def _get_field_type(self, field: Field) -> str:
        """Get Go type for a field."""
        match field.type:
            case FieldType.ARRAY:
                return self._get_array_type(field)
            case FieldType.OBJECT:
                return self._get_object_type(field)
            case _:
                return self.go_config.get_go_type(
                    field.type,
                    is_optional=field.optional,
                )

    def _get_array_type(self, field: Field) -> str:
        """Get Go type for array fields."""
        if field.array_element_schema:
            # Array of objects
            element_type = self.names.type_name(field.array_element_schema)
        elif field.array_element_type and field.array_element_type != FieldType.UNKNOWN:
            # Array of primitives
            element_type = self.go_config.type_map[field.array_element_type]
        else:
            element_type = UNKNOWN_TYPE

        return f"[]{element_type}"

    def _get_object_type(self, field: Field) -> str:
        """Get Go type for object fields."""
        if field.nested_schema:
            struct_name = self.names.type_name(field.nested_schema)

            # Add pointer for optional nested structs if configured
            if field.optional and self.go_config.use_pointers_for_optional:
                return f"*{struct_name}"

            return struct_name

        return UNKNOWN_TYPE

    def _generate_json_tag(self, field: Field) -> str:
        """Struct tag mapping the field to its JSON key."""
        return go_json_tag(
            field.original_name,
            omitempty=field.optional and self.config.json_tag_omitempty,
        )

    @property
    def names(self) -> NamePlan:
        if self._names is None:
            raise RuntimeError("names are planned at the start of generate()")
        return self._names

    def _get_imports(self) -> list[str]:
        """Get required imports based on types used."""
        imports = self.go_config.get_required_imports(self.types_used)
        logger.debug("Generated %s imports", len(imports))
        return imports

    def _get_generation_order(
        self,
        schemas: dict[str, Schema],
        root_name: str,
    ) -> list[str]:
        """
        Determine order for generating structs (dependencies first).

        Uses topological sort to ensure nested types are defined
        before their parent types.
        """
        visited: set[str] = set()
        visiting: set[str] = set()
        ordered: list[str] = []

        def visit(schema_name: str) -> None:
            if schema_name in visited or schema_name not in schemas:
                return

            if schema_name in visiting:
                # Circular dependency detected - skip
                logger.warning("Circular dependency detected: %s", schema_name)
                return

            visiting.add(schema_name)
            schema = schemas[schema_name]

            # Visit dependencies first
            for field in schema.fields:
                if field.nested_schema and field.nested_schema.name in schemas:
                    visit(field.nested_schema.name)

                if (
                    field.array_element_schema
                    and field.array_element_schema.name in schemas
                ):
                    visit(field.array_element_schema.name)

            visiting.remove(schema_name)
            visited.add(schema_name)
            ordered.append(schema_name)

        # Visit all schemas
        for schema_name in schemas:
            visit(schema_name)

        logger.debug("Generation order determined: %s schemas", len(ordered))
        return ordered
