"""
Python code generator module.

Generates Python dataclasses, Pydantic models, and TypedDict from JSON schema analysis.
"""

from .generator import (
    PythonGenerator,
    create_python_generator,
    create_dataclass_generator,
    create_pydantic_generator,
    create_typeddict_generator,
)
from .naming import create_python_sanitizer
from .config import (
    PythonConfig,
    PythonStyle,
    get_python_reserved_words,
    get_python_builtin_types,
    get_dataclass_config,
    get_pydantic_config,
    get_typeddict_config,
    get_strict_dataclass_config,
)
from .interactive import PythonInteractiveHandler

__all__ = [
    # Generator
    "PythonGenerator",
    "create_python_generator",
    "create_dataclass_generator",
    "create_pydantic_generator",
    "create_typeddict_generator",
    # Naming
    "create_python_sanitizer",
    # Configuration
    "PythonConfig",
    "PythonStyle",
    "get_python_reserved_words",
    "get_python_builtin_types",
    "get_dataclass_config",
    "get_pydantic_config",
    "get_typeddict_config",
    "get_strict_dataclass_config",
    # Interactive
    "PythonInteractiveHandler",
]
