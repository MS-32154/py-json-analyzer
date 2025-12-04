"""
Go code generator implementation.

Generates Go structs with JSON tags using templates.
"""

from pathlib import Path
from typing import Any

from ...core.config import GeneratorConfig
from ...core.generator import CodeGenerator
from ...core.schema import Schema, Field, FieldType
from .config import GoConfig
from .naming import create_go_name_tracker

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Go Code Generator
# ============================================================================


class GoGenerator(CodeGenerator):
    """Code generator for Go structs with JSON tags."""

    __slots__ = ("go_config", "name_tracker", "types_used")

    def __init__(self, config: GeneratorConfig):
        """Initialize Go generator with configuration."""
        # Initialize Go-specific config from language_config
        self.go_config = GoConfig(**config.language_config)

        # Initialize naming
        self.name_tracker = create_go_name_tracker()

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
        logger.info(f"Generating Go code for {len(schemas)} schemas")

        # Reset state
        self.types_used.clear()
        self.name_tracker.reset()

        # Generate structs in dependency order
        generation_order = self._get_generation_order(schemas, root_schema_name)
        structs = []

        for schema_name in generation_order:
            if schema_name in schemas:
                struct_data = self._generate_struct_data(schemas[schema_name])
                structs.append(struct_data)

        logger.debug(f"Generated {len(structs)} structs")

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
        case_style = self.config.struct_case
        struct_name = self.name_tracker.sanitize(schema.name, case_style)

        fields = []
        for field in schema.fields:
            field_data = self._generate_field_data(field)
            if field_data:
                fields.append(field_data)

        logger.debug(f"Generated struct: {struct_name} with {len(fields)} fields")

        return {
            "struct_name": struct_name,
            "description": schema.description if self.config.add_comments else None,
            "fields": fields,
        }

    def _generate_field_data(self, field: Field) -> dict[str, Any]:
        """Generate field data for template."""
        # Sanitize field name to PascalCase for Go
        case_style = self.config.field_case
        field_name = self.name_tracker.sanitize(field.name, case_style)

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

        # Generate JSON tag if enabled
        if self.config.generate_json_tags:
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
            element_name = self.name_tracker.sanitize(
                field.array_element_schema.name,
                "pascal",
            )
            element_type = element_name
        elif field.array_element_type and field.array_element_type != FieldType.UNKNOWN:
            # Array of primitives
            element_type = self.go_config.type_map.get(
                field.array_element_type,
                self.go_config.unknown_type,
            )
        else:
            # Unknown array element type
            element_type = self.go_config.unknown_type

        return f"[]{element_type}"

    def _get_object_type(self, field: Field) -> str:
        """Get Go type for object fields."""
        if field.nested_schema:
            struct_name = self.name_tracker.sanitize(
                field.nested_schema.name,
                "pascal",
            )

            # Add pointer for optional nested structs if configured
            if field.optional and self.go_config.use_pointers_for_optional:
                return f"*{struct_name}"

            return struct_name

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

    def _get_imports(self) -> list[str]:
        """Get required imports based on types used."""
        imports = self.go_config.get_required_imports(self.types_used)
        logger.debug(f"Generated {len(imports)} imports")
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
                logger.warning(f"Circular dependency detected: {schema_name}")
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

        logger.debug(f"Generation order determined: {len(ordered)} schemas")
        return ordered

    # ========================================================================
    # Validation
    # ========================================================================

    def validate_schemas(self, schemas: dict[str, Schema]) -> list[str]:
        """Validate schemas for Go generation."""
        warnings = super().validate_schemas(schemas)

        # Add Go-specific validations
        for schema in schemas.values():
            if not schema.fields:
                warnings.append(
                    f"Schema '{schema.name}' has no fields - will generate empty struct"
                )

        return warnings


# ============================================================================
# Factory Functions
# ============================================================================


def create_go_generator(config: GeneratorConfig | None = None) -> GoGenerator:
    """
    Create a Go generator with default configuration.

    Args:
        config: Optional configuration (uses defaults if None)

    Returns:
        Configured GoGenerator instance
    """
    if config is None:
        config = GeneratorConfig(
            package_name="main",
            generate_json_tags=True,
            json_tag_omitempty=True,
            add_comments=True,
        )

    return GoGenerator(config)


def create_web_api_generator() -> GoGenerator:
    """Create generator optimized for web API models."""
    from .config import get_web_api_config

    config = GeneratorConfig(
        package_name="models",
        generate_json_tags=True,
        json_tag_omitempty=True,
        add_comments=True,
        language_config=get_web_api_config().to_dict(),
    )
    return GoGenerator(config)


def create_strict_generator() -> GoGenerator:
    """Create generator with strict types (no pointers)."""
    from .config import get_strict_config

    config = GeneratorConfig(
        package_name="types",
        generate_json_tags=True,
        json_tag_omitempty=False,
        add_comments=True,
        language_config=get_strict_config().to_dict(),
    )
    return GoGenerator(config)
