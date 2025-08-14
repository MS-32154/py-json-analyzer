"""
Base generator interface for all code generation targets.

Defines the contract that all language generators must implement.
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from .schema import Schema, Field, FieldType


class GeneratorError(Exception):
    """Base exception for code generation errors."""
    pass


class CodeGenerator(ABC):
    """Abstract base class for all code generators."""
    
    def __init__(self, config: Optional[Dict[str, Any]] = None):
        """Initialize generator with optional configuration."""
        self.config = config or {}
    
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
    
    @abstractmethod
    def generate_single_schema(self, schema: Schema) -> str:
        """
        Generate code for a single schema.
        
        Args:
            schema: Schema to generate code for
        
        Returns:
            Generated code for this schema only
        """
        pass
    
    @abstractmethod
    def map_field_type(self, field: Field) -> str:
        """
        Map a field to the target language's type system.
        
        Args:
            field: Field to get type for
        
        Returns:
            Type name in target language
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
    
    def get_package_declaration(self) -> Optional[str]:
        """
        Get package/namespace declaration if needed.
        
        Returns:
            Package declaration string or None
        """
        return None
    
    def validate_schemas(self, schemas: Dict[str, Schema]) -> List[str]:
        """
        Validate schemas for this generator and return any warnings.
        
        Args:
            schemas: Schemas to validate
        
        Returns:
            List of warning messages (empty if no issues)
        """
        warnings = []
        
        for schema in schemas.values():
            for field in schema.fields:
                if field.type == FieldType.CONFLICT:
                    warnings.append(
                        f"Type conflict in {schema.name}.{field.name}: "
                        f"{[t.value for t in field.conflicting_types]}"
                    )
                elif field.type == FieldType.UNKNOWN:
                    warnings.append(
                        f"Unknown type in {schema.name}.{field.name}"
                    )
        
        return warnings
    
    def format_code(self, code: str) -> str:
        """
        Apply language-specific formatting to generated code.
        
        Args:
            code: Raw generated code
        
        Returns:
            Formatted code
        """
        return code  # Default: no formatting


class GenerationResult:
    """Container for generation results and metadata."""
    
    def __init__(self, code: str, warnings: List[str] = None, metadata: Dict[str, Any] = None):
        """
        Initialize generation result.
        
        Args:
            code: Generated code
            warnings: Any warnings from generation
            metadata: Additional metadata about generation
        """
        self.code = code
        self.warnings = warnings or []
        self.metadata = metadata or {}
        self.success = True
    
    @classmethod
    def error(cls, message: str, exception: Exception = None) -> 'GenerationResult':
        """Create a failed generation result."""
        result = cls(code="")
        result.success = False
        result.error_message = message
        result.exception = exception
        return result


def generate_code(generator: CodeGenerator, schemas: Dict[str, Schema], 
                 root_schema_name: str) -> GenerationResult:
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
            "root_schema": root_schema_name
        }
        
        return GenerationResult(formatted_code, warnings, metadata)
        
    except Exception as e:
        return GenerationResult.error(
            f"Code generation failed: {str(e)}", 
            exception=e
        )
