"""
Python code generator implementation.

Generates Python dataclasses, Pydantic models, or TypedDict using templates.
"""

from pathlib import Path
from typing import Any

from json_explorer.logging_config import get_logger

from ...core.config import GeneratorConfig
from ...core.generator import CodeGenerator
from ...core.naming import NamePlan, plan_names
from ...core.schema import Field, FieldType, Schema
from .config import PythonConfig, PythonStyle
from .naming import is_plain_key, python_class_name, python_field_name

logger = get_logger(__name__)


# ============================================================================
# Python Code Generator
# ============================================================================


class PythonGenerator(CodeGenerator):
    """Code generator for Python dataclasses, Pydantic models, and TypedDict."""

    __slots__ = ("_names", "python_config", "types_used")

    def __init__(self, config: GeneratorConfig):
        """Initialize Python generator with configuration."""
        # Initialize Python-specific config
        self.python_config = PythonConfig(**config.language_config)

        # Identifiers for the current run (see generate())
        self._names: NamePlan | None = None

        # Track types and optional fields for imports
        self.types_used: set[str] = set()

        # Call parent init (sets up templates)
        super().__init__(config)

        logger.info(
            "PythonGenerator initialized (style: %s)", self.python_config.style.value
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
        logger.info("Generating Python code for %s schemas", len(schemas))

        # Reset state
        self.types_used.clear()
        self._names = plan_names(
            schemas.values(),
            type_identifier=python_class_name,
            field_identifier=self._field_identifier,
            field_separator="_",
        )

        # Generate classes in dependency order
        generation_order = self._get_generation_order(schemas, root_schema_name)
        classes = []

        for schema_name in generation_order:
            if schema_name in schemas:
                class_data = self._generate_class_data(schemas[schema_name])
                classes.append(class_data)

        logger.debug("Generated %s classes", len(classes))

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
        class_name = self.names.type_name(schema)

        fields = []
        for field in schema.fields:
            field_data = self._generate_field_data(field)
            if field_data:
                fields.append(field_data)

        # Positional dataclass fields with a default must come after those
        # without one, or Python raises TypeError when the class is created.
        # Stable sort: JSON order is kept within each group.
        if (
            self.python_config.style == PythonStyle.DATACLASS
            and not self.python_config.dataclass_kw_only
        ):
            fields.sort(key=lambda f: bool(f.get("use_default")))

        logger.debug("Generated class: %s with %s fields", class_name, len(fields))

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
                # Keys that aren't identifiers need TypedDict("Name", {...})
                class_data["functional"] = not all(
                    is_plain_key(f.original_name) for f in schema.fields
                )

        return class_data

    def _field_identifier(self, key: str) -> str:
        """Field name for a JSON key in the configured style."""
        match self.python_config.style:
            case PythonStyle.TYPEDDICT:
                # A TypedDict describes the dict as-is: keys stay unchanged
                return key
            case PythonStyle.PYDANTIC:
                return python_field_name(key, pydantic=True)
            case _:
                return python_field_name(key)

    @property
    def names(self) -> NamePlan:
        if self._names is None:
            raise RuntimeError("names are planned at the start of generate()")
        return self._names

    def _generate_field_data(self, field: Field) -> dict[str, Any]:
        """Generate field data for template."""
        field_name = self.names.field_name(field)

        # Determine Python type
        python_type = self._get_field_type(field)
        self.types_used.add(python_type)

        field_data = {
            "name": field_name,
            "type": python_type,
            "original_name": field.original_name,
            "key": repr(field.original_name),  # as a Python string literal
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
                field_config = []
                # The alias maps the field to its JSON key
                if field.original_name != field_name:
                    field_config.append(f"alias={field.original_name!r}")
                if field.description and self.config.add_comments:
                    field_config.append(f"description={field.description!r}")
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
            element_type = self.names.type_name(field.array_element_schema)
        elif field.array_element_type and field.array_element_type != FieldType.UNKNOWN:
            # Array of primitives
            element_type = self.python_config.type_map[field.array_element_type]
        else:
            element_type = "Any"

        base_type = f"list[{element_type}]"
        return self.python_config.optional(base_type) if field.optional else base_type

    def _get_object_type(self, field: Field) -> str:
        """Get Python type for object fields."""
        if field.nested_schema:
            class_name = self.names.type_name(field.nested_schema)
            return (
                self.python_config.optional(class_name)
                if field.optional
                else class_name
            )

        return self.python_config.get_python_type(
            FieldType.UNKNOWN,
            is_optional=field.optional,
        )

    def _get_imports(self) -> list[str]:
        """Get required imports based on types used."""
        imports = self.python_config.get_required_imports(self.types_used)
        logger.debug("Generated %s imports", len(imports))
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
