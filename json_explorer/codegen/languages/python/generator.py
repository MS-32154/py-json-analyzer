"""
Python code generator implementation.

Generates Python dataclasses, Pydantic models, or TypedDict using templates.
"""

from typing import Dict, List, Any
from pathlib import Path
from ...core.generator import CodeGenerator
from ...core.schema import Schema, Field, FieldType
from ...core.naming import NamingCase
from ...core.config import GeneratorConfig
from .naming import create_python_sanitizer
from .config import PythonConfig, PythonStyle


class PythonGenerator(CodeGenerator):
    """Code generator for Python dataclasses, Pydantic models, and TypedDict."""

    def __init__(self, config: GeneratorConfig):
        """Initialize Python generator with configuration."""
        super().__init__(config)

        # Initialize naming
        self.sanitizer = create_python_sanitizer()

        # Initialize Python-specific configuration
        self.python_config = PythonConfig(**config.language_config)

        # State tracking
        self.generated_classes = set()
        self.types_used = set()
        self.has_optional_fields = False

    @property
    def language_name(self) -> str:
        """Return the language name."""
        return "python"

    @property
    def file_extension(self) -> str:
        """Return Python file extension."""
        return ".py"

    def get_template_directory(self) -> Path:
        """Return the Python templates directory."""
        return Path(__file__).parent / "templates"

    def generate(self, schemas: Dict[str, Schema], root_schema_name: str) -> str:
        """Generate complete Python code for all schemas."""
        # Reset state
        self.generated_classes.clear()
        self.types_used.clear()
        self.has_optional_fields = False
        self.sanitizer.reset_used_names()

        # Generate classes in dependency order
        generation_order = self._get_generation_order(schemas, root_schema_name)
        classes = []

        for schema_name in generation_order:
            if schema_name in schemas and schema_name not in self.generated_classes:
                class_data = self._generate_class_data(schemas[schema_name])
                classes.append(class_data)
                self.generated_classes.add(schema_name)

        # Get required imports
        imports = self._get_imports()

        # Render complete file
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
        style_templates = {
            PythonStyle.DATACLASS: "dataclass_file.py.j2",
            PythonStyle.PYDANTIC: "pydantic_file.py.j2",
            PythonStyle.TYPEDDICT: "typeddict_file.py.j2",
        }
        return style_templates.get(self.python_config.style, "dataclass_file.py.j2")

    def _generate_class_data(self, schema: Schema) -> Dict[str, Any]:
        """Generate class data for template."""
        class_name = self.sanitizer.sanitize_name(schema.name, NamingCase.PASCAL_CASE)

        fields = []
        for field in schema.fields:
            field_data = self._generate_field_data(field, schema.name)
            if field_data:
                fields.append(field_data)

        class_data = {
            "class_name": class_name,
            "description": schema.description if self.config.add_comments else None,
            "fields": fields,
            "style": self.python_config.style,
        }

        # Add style-specific metadata
        if self.python_config.style == PythonStyle.DATACLASS:
            class_data["frozen"] = self.python_config.dataclass_frozen
            class_data["slots"] = self.python_config.dataclass_slots
            class_data["kw_only"] = self.python_config.dataclass_kw_only

        elif self.python_config.style == PythonStyle.PYDANTIC:
            class_data["config_dict"] = self.python_config.pydantic_config_dict
            class_data["extra_forbid"] = self.python_config.pydantic_extra_forbid

        elif self.python_config.style == PythonStyle.TYPEDDICT:
            class_data["total"] = self.python_config.typeddict_total

        return class_data

    def _generate_field_data(self, field: Field, schema_context: str) -> Dict[str, Any]:
        """Generate field data for template."""
        # Generate field name
        field_name = self.sanitizer.sanitize_name(field.name, NamingCase.SNAKE_CASE)

        # Determine Python type
        python_type = self._get_field_type(field, schema_context)
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
        if self.python_config.style == PythonStyle.DATACLASS:
            field_data["use_default"] = field.optional
            if field.optional:
                field_data["default_value"] = "None"

        elif self.python_config.style == PythonStyle.PYDANTIC:
            # Pydantic Field configuration
            if self.python_config.pydantic_use_field:
                field_config = []

                if (
                    self.python_config.pydantic_use_alias
                    and field.original_name != field_name
                ):
                    field_config.append(f'alias="{field.original_name}"')

                if field.description and self.config.add_comments:
                    # Escape quotes in description
                    desc = field.description.replace('"', '\\"')
                    field_config.append(f'description="{desc}"')

                if field.optional:
                    field_config.append("default=None")

                if field_config:
                    field_data["field_config"] = ", ".join(field_config)

        return field_data

    def _get_field_type(self, field: Field, schema_context: str) -> str:
        """Get Python type for a field."""
        if field.type == FieldType.ARRAY:
            return self._get_array_type(field, schema_context)
        elif field.type == FieldType.OBJECT:
            return self._get_object_type(field, schema_context)
        else:
            return self.python_config.get_python_type(
                field.type, is_optional=field.optional
            )

    def _get_array_type(self, field: Field, schema_context: str) -> str:
        """Get Python type for array fields."""
        if field.array_element_type and field.array_element_type != FieldType.UNKNOWN:
            element_type = self.python_config.type_map.get(
                field.array_element_type, self.python_config.unknown_type
            )
        elif field.array_element_schema:
            element_name = self.sanitizer.sanitize_name(
                field.array_element_schema.name, NamingCase.PASCAL_CASE
            )
            element_type = element_name
        else:
            element_type = self.python_config.unknown_type

        base_type = f"list[{element_type}]"

        # Add optional wrapper if needed
        if field.optional and self.python_config.use_optional:
            if self.python_config.style == PythonStyle.TYPEDDICT:
                return f"NotRequired[{base_type}]"
            else:
                return f"{base_type} | None"

        return base_type

    def _get_object_type(self, field: Field, schema_context: str) -> str:
        """Get Python type for object fields."""
        if field.nested_schema:
            class_name = self.sanitizer.sanitize_name(
                field.nested_schema.name, NamingCase.PASCAL_CASE
            )

            # Add optional wrapper if needed
            if field.optional and self.python_config.use_optional:
                if self.python_config.style == PythonStyle.TYPEDDICT:
                    return f"NotRequired[{class_name}]"
                else:
                    return f"{class_name} | None"
            return class_name
        else:
            return self.python_config.get_python_type(
                FieldType.UNKNOWN, is_optional=field.optional
            )

    def _get_imports(self) -> List[str]:
        """Get required imports based on types used."""
        imports = self.python_config.get_required_imports(
            self.types_used, self.has_optional_fields
        )

        # Sort imports: standard library, then third-party
        sorted_imports = sorted(
            list(imports),
            key=lambda x: (
                (
                    0
                    if x.startswith("from typing") or x.startswith("from datetime")
                    else 1
                ),
                x,
            ),
        )

        return sorted_imports

    def get_import_statements(self, schemas: Dict[str, Schema]) -> List[str]:
        """Get required import statements."""
        return self._get_imports()

    def _get_generation_order(
        self, schemas: Dict[str, Schema], root_name: str
    ) -> List[str]:
        """Determine order for generating classes to handle dependencies."""
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
        """Validate schemas for Python generation."""
        warnings = super().validate_schemas(schemas)

        # Add Python-specific validations
        for schema in schemas.values():
            if not schema.fields:
                warnings.append(
                    f"Schema {schema.name} has no fields - will generate empty class"
                )

            # Check for potential naming conflicts
            for field in schema.fields:
                sanitized = self.sanitizer.sanitize_name(
                    field.name, NamingCase.SNAKE_CASE
                )
                if sanitized != field.name.lower().replace("-", "_"):
                    warnings.append(
                        f"Field {schema.name}.{field.name} renamed to {sanitized}"
                    )

        # Style-specific warnings
        if self.python_config.style == PythonStyle.TYPEDDICT:
            warnings.append(
                "TypedDict classes are type hints only - no runtime validation"
            )

        return warnings


# Factory functions
def create_python_generator(
    config: GeneratorConfig = None, style: str = "dataclass"
) -> PythonGenerator:
    """Create a Python generator with specified style."""
    if config is None:
        from ...core.config import GeneratorConfig

        config = GeneratorConfig(
            package_name="models",
            add_comments=True,
            language_config={"style": style},
        )

    return PythonGenerator(config)


def create_dataclass_generator() -> PythonGenerator:
    """Create generator for Python dataclasses."""
    from ...core.config import GeneratorConfig
    from .config import get_dataclass_config

    config = GeneratorConfig(
        package_name="models",
        add_comments=True,
        language_config=get_dataclass_config().__dict__,
    )

    return PythonGenerator(config)


def create_pydantic_generator() -> PythonGenerator:
    """Create generator for Pydantic v2 models."""
    from ...core.config import GeneratorConfig
    from .config import get_pydantic_config

    config = GeneratorConfig(
        package_name="models",
        add_comments=True,
        language_config=get_pydantic_config().__dict__,
    )

    return PythonGenerator(config)


def create_typeddict_generator() -> PythonGenerator:
    """Create generator for TypedDict classes."""
    from ...core.config import GeneratorConfig
    from .config import get_typeddict_config

    config = GeneratorConfig(
        package_name="types",
        add_comments=True,
        language_config=get_typeddict_config().__dict__,
    )

    return PythonGenerator(config)
