"""
Python code generator implementation.

Generates Python dataclasses, Pydantic models, or TypedDict using templates.
"""

from pathlib import Path
from typing import Any

from ...core.config import GeneratorConfig
from ...core.generator import CodeGenerator
from ...core.schema import Schema, Field, FieldType
from .config import PythonConfig, PythonStyle, get_python_generator_config
from .naming import create_python_name_tracker

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Python Code Generator
# ============================================================================


class PythonGenerator(CodeGenerator):
    """Code generator for Python dataclasses, Pydantic models, and TypedDict."""

    __slots__ = ("python_config", "name_tracker", "types_used", "has_optional_fields")

    def __init__(self, config: GeneratorConfig):
        """Initialize Python generator with configuration."""
        # Initialize Python-specific config
        self.python_config = PythonConfig(**config.language_config)

        # Initialize naming
        self.name_tracker = create_python_name_tracker()

        # Track types and optional fields for imports
        self.types_used: set[str] = set()
        self.has_optional_fields = False

        # Call parent init (sets up templates)
        super().__init__(config)

        logger.info(
            f"PythonGenerator initialized (style: {self.python_config.style.value})"
        )

    # ========================================================================
    # Required Properties
    # ========================================================================

    @property
    def language_name(self) -> str:
        """Return language name."""
        return "python"

    @property
    def file_extension(self) -> str:
        """Return Python file extension."""
        return ".py"

    def get_template_directory(self) -> Path:
        """Return Python templates directory."""
        return Path(__file__).parent / "templates"

    # ========================================================================
    # Code Generation
    # ========================================================================

    def generate(
        self,
        schemas: dict[str, Schema],
        root_schema_name: str,
    ) -> str:
        """Generate complete Python code for all schemas."""
        logger.info(f"Generating Python code for {len(schemas)} schemas")

        # Reset state
        self.types_used.clear()
        self.has_optional_fields = False
        self.name_tracker.reset()

        # Generate classes in dependency order
        generation_order = self._get_generation_order(schemas, root_schema_name)
        classes = []

        for schema_name in generation_order:
            if schema_name in schemas:
                class_data = self._generate_class_data(schemas[schema_name])
                classes.append(class_data)

        logger.debug(f"Generated {len(classes)} classes")

        # Get required imports
        imports = self._get_imports()

        # Render complete file with appropriate template
        template_name = self._get_template_name()
        context = {
            "imports": imports,
            "classes": classes,
            "style": self.python_config.style.value,
            "config": self.python_config,
        }

        return self.render_template(template_name, context)

    def _get_template_name(self) -> str:
        """Get the appropriate template based on style."""
        match self.python_config.style:
            case PythonStyle.DATACLASS:
                return "dataclass_file.py.j2"
            case PythonStyle.PYDANTIC:
                return "pydantic_file.py.j2"
            case PythonStyle.TYPEDDICT:
                return "typeddict_file.py.j2"
            case _:
                return "dataclass_file.py.j2"

    def _generate_class_data(self, schema: Schema) -> dict[str, Any]:
        """Generate class data for template."""
        case_style = self.config.struct_case
        class_name = self.name_tracker.sanitize(schema.name, case_style)

        fields = []
        for field in schema.fields:
            field_data = self._generate_field_data(field)
            if field_data:
                fields.append(field_data)

        logger.debug(f"Generated class: {class_name} with {len(fields)} fields")

        class_data = {
            "class_name": class_name,
            "description": schema.description if self.config.add_comments else None,
            "fields": fields,
            "style": self.python_config.style,
        }

        # Add style-specific metadata
        match self.python_config.style:
            case PythonStyle.DATACLASS:
                class_data["frozen"] = self.python_config.dataclass_frozen
                class_data["slots"] = self.python_config.dataclass_slots
                class_data["kw_only"] = self.python_config.dataclass_kw_only

            case PythonStyle.PYDANTIC:
                class_data["config_dict"] = self.python_config.pydantic_config_dict
                class_data["extra_forbid"] = self.python_config.pydantic_extra_forbid

            case PythonStyle.TYPEDDICT:
                class_data["total"] = self.python_config.typeddict_total

        return class_data

    def _generate_field_data(self, field: Field) -> dict[str, Any]:
        """Generate field data for template."""
        # Sanitize field name to snake_case for Python
        case_style = self.config.field_case
        field_name = self.name_tracker.sanitize(field.name, case_style)

        # Determine Python type
        python_type = self._get_field_type(field)
        self.types_used.add(python_type)

        # Track optional fields
        if field.optional:
            self.has_optional_fields = True

        field_data = {
            "name": field_name,
            "type": python_type,
            "original_name": field.original_name,
            "optional": field.optional,
        }

        # Add comment if enabled
        if self.config.add_comments and field.description:
            field_data["comment"] = field.description

        # Add style-specific field metadata
        match self.python_config.style:
            case PythonStyle.DATACLASS:
                field_data["use_default"] = field.optional
                if field.optional:
                    field_data["default_value"] = "None"

            case PythonStyle.PYDANTIC:
                # Pydantic Field configuration
                if self.python_config.pydantic_use_field:
                    field_config = []

                    # Alias for original JSON key
                    if (
                        self.python_config.pydantic_use_alias
                        and field.original_name != field_name
                    ):
                        field_config.append(f'alias="{field.original_name}"')

                    # Description
                    if field.description and self.config.add_comments:
                        desc = field.description.replace('"', '\\"')
                        field_config.append(f'description="{desc}"')

                    # Default for optional
                    if field.optional:
                        field_config.append("default=None")

                    if field_config:
                        field_data["field_config"] = ", ".join(field_config)

        return field_data

    def _get_field_type(self, field: Field) -> str:
        """Get Python type for a field."""
        match field.type:
            case FieldType.ARRAY:
                return self._get_array_type(field)
            case FieldType.OBJECT:
                return self._get_object_type(field)
            case _:
                return self.python_config.get_python_type(
                    field.type,
                    is_optional=field.optional,
                )

    def _get_array_type(self, field: Field) -> str:
        """Get Python type for array fields."""
        if field.array_element_schema:
            # Array of objects
            element_name = self.name_tracker.sanitize(
                field.array_element_schema.name,
                "pascal",
            )
            element_type = element_name
        elif field.array_element_type and field.array_element_type != FieldType.UNKNOWN:
            # Array of primitives
            element_type = self.python_config.type_map.get(
                field.array_element_type,
                self.python_config.unknown_type,
            )
        else:
            # Unknown array element type
            element_type = self.python_config.unknown_type

        base_type = f"list[{element_type}]"

        # Add optional wrapper if needed
        if field.optional and self.python_config.use_optional:
            match self.python_config.style:
                case PythonStyle.TYPEDDICT:
                    return f"NotRequired[{base_type}]"
                case _:
                    return f"{base_type} | None"

        return base_type

    def _get_object_type(self, field: Field) -> str:
        """Get Python type for object fields."""
        if field.nested_schema:
            class_name = self.name_tracker.sanitize(
                field.nested_schema.name,
                "pascal",
            )

            # Add optional wrapper if needed
            if field.optional and self.python_config.use_optional:
                match self.python_config.style:
                    case PythonStyle.TYPEDDICT:
                        return f"NotRequired[{class_name}]"
                    case _:
                        return f"{class_name} | None"

            return class_name

        return self.python_config.get_python_type(
            FieldType.UNKNOWN,
            is_optional=field.optional,
        )

    def _get_imports(self) -> list[str]:
        """Get required imports based on types used."""
        imports = self.python_config.get_required_imports(
            self.types_used,
            self.has_optional_fields,
        )
        logger.debug(f"Generated {len(imports)} imports")
        return imports

    def _get_generation_order(
        self,
        schemas: dict[str, Schema],
        root_name: str,
    ) -> list[str]:
        """Determine order for generating classes (dependencies first)."""
        visited: set[str] = set()
        visiting: set[str] = set()
        ordered: list[str] = []

        def visit(schema_name: str) -> None:
            if schema_name in visited or schema_name not in schemas:
                return

            if schema_name in visiting:
                # Circular dependency detected
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
        """Validate schemas for Python generation."""
        warnings = super().validate_schemas(schemas)

        # Add Python-specific validations
        for schema in schemas.values():
            if not schema.fields:
                warnings.append(
                    f"Schema '{schema.name}' has no fields - will generate empty class"
                )

        # Style-specific warnings
        match self.python_config.style:
            case PythonStyle.TYPEDDICT:
                warnings.append(
                    "TypedDict classes are type hints only - no runtime validation"
                )

        return warnings


# ============================================================================
# Factory Functions
# ============================================================================


def create_python_generator(
    config: GeneratorConfig | None = None,
    style: str = "dataclass",
) -> PythonGenerator:
    """
    Create a Python generator with specified style.

    Args:
        config: Optional configuration
        style: Python style (dataclass, pydantic, typeddict)

    Returns:
        Configured PythonGenerator instance
    """
    if config is None:
        config = GeneratorConfig(
            package_name="models",
            add_comments=True,
            language_config={"style": style},
        )

    return PythonGenerator(config)


def create_dataclass_generator() -> PythonGenerator:
    """Create generator for Python dataclasses."""
    from .config import get_dataclass_config

    config = GeneratorConfig(
        **get_python_generator_config(),
        language_config=get_dataclass_config().to_dict(),
    )

    return PythonGenerator(config)


def create_pydantic_generator() -> PythonGenerator:
    """Create generator for Pydantic v2 models."""
    from .config import get_pydantic_config

    config = GeneratorConfig(
        **get_python_generator_config(),
        language_config=get_pydantic_config().to_dict(),
    )

    return PythonGenerator(config)


def create_typeddict_generator() -> PythonGenerator:
    """Create generator for TypedDict classes."""
    from .config import get_typeddict_config

    config = GeneratorConfig(
        **get_python_generator_config(),
        language_config=get_typeddict_config().to_dict(),
    )

    return PythonGenerator(config)
