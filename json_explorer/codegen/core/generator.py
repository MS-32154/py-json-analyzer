"""
Base generator interface for all code generation targets.

Defines the contract that all language generators must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any
from pathlib import Path
from .schema import Schema, FieldType
from .config import GeneratorConfig
from .templates import TemplateEngine, create_template_engine


class GeneratorError(Exception):
    """Base exception for code generation errors."""

    pass


class CodeGenerator(ABC):
    """Abstract base class for all code generators."""

    def __init__(self, config: GeneratorConfig):
        """Initialize generator with configuration."""
        self.config = config
        self._template_engine = None
        self._setup_templates()

    def _setup_templates(self):
        """Setup template engine for this generator."""
        template_dir = self.get_template_directory()
        if template_dir and template_dir.exists():
            self._template_engine = create_template_engine(template_dir)
        else:
            raise GeneratorError(f"Template directory not found: {template_dir}")

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Return the name of the target language (e.g., 'go', 'python')."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return the file extension for generated files (e.g., '.go', '.py')."""
        pass

    @abstractmethod
    def get_template_directory(self) -> Path:
        """Return the directory containing templates for this generator."""
        pass

    @property
    def template_engine(self) -> TemplateEngine:
        """Get the template engine for this generator."""
        return self._template_engine

    @abstractmethod
    def generate(self, schemas: Dict[str, Schema], root_schema_name: str) -> str:
        """
        Generate code for all schemas.

        Args:
            schemas: Dictionary mapping schema names to Schema objects
            root_schema_name: Name of the main/root schema

        Returns:
            Generated code as a string
        """
        pass

    def get_import_statements(self, schemas: Dict[str, Schema]) -> List[str]:
        """
        Get any required import statements for the generated code.

        Args:
            schemas: All schemas being generated

        Returns:
            List of import statements (can be empty)
        """
        return []

    def validate_schemas(self, schemas: Dict[str, Schema]) -> List[str]:
        """
        Validate schemas for basic structural issues.

        Args:
            schemas: Schemas to validate

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        for schema in schemas.values():
            # Check for empty schemas
            if not schema.fields:
                warnings.append(f"Schema '{schema.name}' has no fields")

            # Check for schema-level conflicts and unknowns
            for field in schema.fields:
                if field.type == FieldType.CONFLICT:
                    conflicting_type_names = (
                        [t.value for t in field.conflicting_types]
                        if field.conflicting_types
                        else ["unknown"]
                    )
                    warnings.append(
                        f"Type conflict in {schema.name}.{field.name}: {conflicting_type_names}"
                    )
                elif field.type == FieldType.UNKNOWN:
                    warnings.append(f"Unknown type in {schema.name}.{field.name}")

        return warnings

    def format_code(self, code: str) -> str:
        """
        Apply basic formatting to generated code.

        Args:
            code: Raw generated code

        Returns:
            Formatted code
        """
        lines = code.split("\n")
        formatted_lines = []
        blank_count = 0

        for line in lines:
            stripped = line.rstrip()
            if not stripped:
                blank_count += 1
                if blank_count <= 2:  # Allow max 2 consecutive blank lines
                    formatted_lines.append("")
            else:
                blank_count = 0
                formatted_lines.append(stripped)

        return "\n".join(formatted_lines)

    # Template helper methods
    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """Render a template with context."""
        return self.template_engine.render_template(template_name, context)

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        return self.template_engine.template_exists(template_name)


class GenerationResult:
    """Container for generation results and metadata."""

    def __init__(
        self, code: str, warnings: List[str] = None, metadata: Dict[str, Any] = None
    ):
        """Initialize generation result."""
        self.code = code
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.success = True

    @classmethod
    def error(cls, message: str, exception: Exception = None) -> "GenerationResult":
        """Create a failed generation result."""
        result = cls(code="")
        result.success = False
        result.error_message = message
        result.exception = exception
        return result


def generate_code(
    generator: CodeGenerator, schemas: Dict[str, Schema], root_schema_name: str
) -> GenerationResult:
    """
    Generate code using the specified generator with error handling.

    Args:
        generator: Code generator instance
        schemas: Schemas to generate code for
        root_schema_name: Name of the root schema

    Returns:
        GenerationResult with code, warnings, and metadata
    """
    try:
        # Validate schemas
        warnings = generator.validate_schemas(schemas)

        # Generate code
        code = generator.generate(schemas, root_schema_name)

        # Format code
        formatted_code = generator.format_code(code)

        # Create metadata
        metadata = {
            "language": generator.language_name,
            "file_extension": generator.file_extension,
            "schema_count": len(schemas),
            "root_schema": root_schema_name,
        }

        return GenerationResult(formatted_code, warnings, metadata)

    except Exception as e:
        return GenerationResult.error(f"Code generation failed: {str(e)}", exception=e)
