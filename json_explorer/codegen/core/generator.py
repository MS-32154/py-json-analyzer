"""
Base generator interface for code generation.

Defines the contract that all language generators must implement.
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, ClassVar

from json_explorer.errors import JsonExplorerError
from json_explorer.logging_config import get_logger

from .config import GeneratorConfig
from .schema import FieldType, Schema
from .templates import TemplateManager

logger = get_logger(__name__)


# ============================================================================
# Exceptions
# ============================================================================


class GeneratorError(JsonExplorerError):
    """Base exception for code generation errors."""


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
    ) -> GenerationResult:
        """Create a failed generation result."""
        logger.debug("Generation failed: %s", message)
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
                "Generation succeeded: %s chars, %s warnings",
                len(self.code),
                len(self.warnings),
            )
            for warning in self.warnings:
                # Warnings printed out after generated code
                logger.info("  - %s", warning)
        else:
            logger.error("Generation failed: %s", self.error_message)


# ============================================================================
# Abstract Base Generator
# ============================================================================


class CodeGenerator(ABC):
    """Base class for language generators.

    Subclasses set ``language_name``, ``file_extension`` and ``template_dir``
    and implement ``generate``. Per-run state (names, imports) belongs in
    ``generate``'s locals, so one generator instance can be reused.
    """

    language_name: ClassVar[str]
    file_extension: ClassVar[str]
    template_dir: ClassVar[Path]

    __slots__ = ("_templates", "config")

    def __init__(self, config: GeneratorConfig):
        self.config = config
        if not self.template_dir.is_dir():
            raise GeneratorError(f"Template directory not found: {self.template_dir}")
        self._templates = TemplateManager(self.template_dir)

    @abstractmethod
    def generate(self, schemas: dict[str, Schema], root_schema_name: str) -> str:
        """Generate the source code for all schemas."""

    def render_template(self, template_name: str, context: dict[str, Any]) -> str:
        return self._templates.render(template_name, context)

    @staticmethod
    def dependency_order(schemas: dict[str, Schema]) -> list[Schema]:
        """Schemas with nested types before the types that use them.

        JSON data is a tree, so there are no cycles: a post-order walk works.
        """
        ordered: list[Schema] = []
        seen: set[int] = set()

        def visit(schema: Schema) -> None:
            if id(schema) in seen:
                return
            seen.add(id(schema))
            for fld in schema.fields:
                for child in (fld.nested_schema, fld.array_element_schema):
                    if child is not None:
                        visit(child)
            ordered.append(schema)

        for schema in schemas.values():
            visit(schema)
        return ordered

    def validate_schemas(self, schemas: dict[str, Schema]) -> list[str]:
        """Warnings about schemas whose types can't be fully determined."""
        warnings = []
        for schema in schemas.values():
            if not schema.fields:
                warnings.append(f"Schema '{schema.name}' has no fields")
            for fld in schema.fields:
                if fld.type == FieldType.CONFLICT:
                    types = [t.value for t in fld.conflicting_types] or ["unknown"]
                    warnings.append(
                        f"Type conflict in {schema.name}.{fld.name}: {', '.join(types)}"
                    )
                elif fld.type == FieldType.UNKNOWN:
                    warnings.append(f"Unknown type in {schema.name}.{fld.name}")
        return warnings

    def format_code(self, code: str) -> str:
        """Strip trailing whitespace, collapse blank-line runs (max 2), end with one newline."""
        lines: list[str] = []
        blank = 0
        for line in code.split("\n"):
            line = line.rstrip()
            blank = blank + 1 if not line else 0
            if blank <= 2:
                lines.append(line)
        return "\n".join(lines).strip("\n") + "\n"  # exactly one final newline


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
        "Starting code generation: %s, %s schemas, root=%s",
        generator.language_name,
        len(schemas),
        root_schema_name,
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

    except JsonExplorerError as e:  # template/config problems; bugs propagate
        logger.debug("Generation failed with exception", exc_info=True)
        return GenerationResult.error(
            message=f"Code generation failed: {e}",
            exception=e,
        )
