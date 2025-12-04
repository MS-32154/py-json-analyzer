"""
Base generator interface for code generation.

Defines the contract that all language generators must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

from .config import GeneratorConfig
from .schema import Schema, FieldType
from .templates import TemplateManager

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class GeneratorError(Exception):
    """Base exception for code generation errors."""

    pass


# ============================================================================
# Generation Result
# ============================================================================


@dataclass(slots=True, kw_only=True)
class GenerationResult:
    """
    Container for generation results and metadata.

    Attributes:
        success: Whether generation succeeded
        code: Generated code (empty if failed)
        warnings: List of warning messages
        metadata: Additional generation metadata
        error_message: Error message if failed
        exception: Original exception if failed
    """

    success: bool = True
    code: str = ""
    warnings: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    # Error information
    error_message: str | None = None
    exception: Exception | None = None

    @classmethod
    def error(
        cls,
        message: str,
        exception: Exception | None = None,
    ) -> "GenerationResult":
        """Create a failed generation result."""
        logger.error(f"Generation failed: {message}")
        return cls(
            success=False,
            code="",
            error_message=message,
            exception=exception,
        )

    def log_summary(self) -> None:
        """Log generation result summary."""
        if self.success:
            logger.info(
                f"Generation succeeded: {len(self.code)} chars, "
                f"{len(self.warnings)} warnings"
            )
            for warning in self.warnings:
                # Warnings printed out after generated code
                logger.info(f"  - {warning}")
        else:
            logger.error(f"Generation failed: {self.error_message}")


# ============================================================================
# Abstract Base Generator
# ============================================================================


class CodeGenerator(ABC):
    """
    Abstract base class for all code generators.

    Subclasses must implement:
    - language_name: Language identifier
    - file_extension: Output file extension
    - get_template_directory: Path to templates
    - generate: Core generation logic
    """

    __slots__ = ("config", "_template_manager")

    def __init__(self, config: GeneratorConfig):
        """
        Initialize generator with configuration.

        Args:
            config: Generator configuration

        Raises:
            GeneratorError: If template setup fails
        """
        self.config = config
        self._template_manager: TemplateManager | None = None

        logger.info(
            f"Initializing {self.language_name} generator "
            f"(package: {config.package_name})"
        )

        self._setup_templates()

    def _setup_templates(self) -> None:
        """Setup template engine for this generator."""
        template_dir = self.get_template_directory()

        if not template_dir or not template_dir.exists():
            raise GeneratorError(f"Template directory not found: {template_dir}")

        self._template_manager = TemplateManager(template_dir)
        logger.debug(f"Template engine initialized: {template_dir}")

    # ========================================================================
    # Abstract Properties and Methods (Must Implement)
    # ========================================================================

    @property
    @abstractmethod
    def language_name(self) -> str:
        """Return language name (e.g., 'go', 'python')."""
        pass

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Return file extension (e.g., '.go', '.py')."""
        pass

    @abstractmethod
    def get_template_directory(self) -> Path:
        """Return directory containing templates for this generator."""
        pass

    @abstractmethod
    def generate(
        self,
        schemas: dict[str, Schema],
        root_schema_name: str,
    ) -> str:
        """
        Generate code for all schemas.

        Args:
            schemas: Dictionary mapping schema names to Schema objects
            root_schema_name: Name of the main/root schema

        Returns:
            Generated code as string

        Raises:
            GeneratorError: If generation fails
        """
        pass

    # ========================================================================
    # Template Methods (Can Override)
    # ========================================================================

    @property
    def template_manager(self) -> TemplateManager:
        """Get the template manager for this generator."""
        if self._template_manager is None:
            raise GeneratorError("Template manager not initialized")
        return self._template_manager

    def render_template(
        self,
        template_name: str,
        context: dict[str, Any],
    ) -> str:
        """
        Render a template with context.

        Args:
            template_name: Template file name
            context: Variables for template

        Returns:
            Rendered template content
        """
        return self.template_manager.render(template_name, context)

    def template_exists(self, template_name: str) -> bool:
        """Check if template exists."""
        return self.template_manager.exists(template_name)

    def get_import_statements(
        self,
        schemas: dict[str, Schema],
    ) -> list[str]:
        """
        Get required import statements.

        Default implementation returns empty list.
        Override to provide language-specific imports.

        Args:
            schemas: All schemas being generated

        Returns:
            List of import statements
        """
        return []

    def validate_schemas(
        self,
        schemas: dict[str, Schema],
    ) -> list[str]:
        """
        Validate schemas for structural issues.

        Default implementation checks for basic issues.
        Override to add language-specific validations.

        Args:
            schemas: Schemas to validate

        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []

        for schema in schemas.values():
            # Empty schemas
            if not schema.fields:
                warnings.append(f"Schema '{schema.name}' has no fields")

            # Field-level issues
            for field in schema.fields:
                if field.type == FieldType.CONFLICT:
                    type_names = (
                        [t.value for t in field.conflicting_types]
                        if field.conflicting_types
                        else ["unknown"]
                    )
                    warnings.append(
                        f"Type conflict in {schema.name}.{field.name}: "
                        f"{', '.join(type_names)}"
                    )

                elif field.type == FieldType.UNKNOWN:
                    warnings.append(f"Unknown type in {schema.name}.{field.name}")

        if warnings:
            # Warnings printed out after generated code
            logger.info(f"Schema validation found {len(warnings)} issues")

        return warnings

    def format_code(self, code: str) -> str:
        """
        Apply basic formatting to generated code.

        Default implementation:
        - Removes excessive blank lines (max 2 consecutive)
        - Strips trailing whitespace

        Override for language-specific formatting.

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
                if blank_count <= 2:  # Max 2 consecutive blank lines
                    formatted_lines.append("")
            else:
                blank_count = 0
                formatted_lines.append(stripped)

        result = "\n".join(formatted_lines)
        logger.debug(f"Code formatted: {len(code)} → {len(result)} chars")
        return result


# ============================================================================
# High-Level Generation Function
# ============================================================================


def generate_code(
    generator: CodeGenerator,
    schemas: dict[str, Schema],
    root_schema_name: str,
) -> GenerationResult:
    """
    Generate code using specified generator with error handling.

    This is the main entry point for code generation. It:
    1. Validates schemas
    2. Generates code
    3. Formats code
    4. Creates result with metadata

    Args:
        generator: Code generator instance
        schemas: Schemas to generate code for
        root_schema_name: Name of the root schema

    Returns:
        GenerationResult with code, warnings, and metadata
    """
    logger.info(
        f"Starting code generation: {generator.language_name}, "
        f"{len(schemas)} schemas, root={root_schema_name}"
    )

    try:
        # Step 1: Validate
        warnings = generator.validate_schemas(schemas)

        # Step 2: Generate
        logger.debug("Generating code...")
        code = generator.generate(schemas, root_schema_name)

        # Step 3: Format
        logger.debug("Formatting code...")
        formatted_code = generator.format_code(code)

        # Step 4: Create metadata
        metadata = {
            "language": generator.language_name,
            "file_extension": generator.file_extension,
            "schema_count": len(schemas),
            "root_schema": root_schema_name,
            "code_length": len(formatted_code),
            "line_count": formatted_code.count("\n") + 1,
        }

        result = GenerationResult(
            success=True,
            code=formatted_code,
            warnings=warnings,
            metadata=metadata,
        )

        result.log_summary()
        return result

    except Exception as e:
        logger.exception("Generation failed with exception")
        return GenerationResult.error(
            message=f"Code generation failed: {e}",
            exception=e,
        )
