"""
Python code generator module.

Generates Python dataclasses, Pydantic models, and TypedDict from JSON schema analysis.
"""

from .config import (
    PythonConfig,
    PythonStyle,
    get_dataclass_config,
    get_pydantic_config,
    get_strict_dataclass_config,
    get_typeddict_config,
)
from .generator import (
    PythonGenerator,
    create_dataclass_generator,
    create_pydantic_generator,
    create_python_generator,
    create_typeddict_generator,
)
from .interactive import PythonInteractiveHandler
from .naming import create_python_name_tracker

__all__ = [
    # Generator
    "PythonGenerator",
    "create_python_generator",
    "create_dataclass_generator",
    "create_pydantic_generator",
    "create_typeddict_generator",
    # Configuration
    "PythonConfig",
    "PythonStyle",
    "get_dataclass_config",
    "get_pydantic_config",
    "get_typeddict_config",
    "get_strict_dataclass_config",
    # Naming
    "create_python_name_tracker",
    # Interactive
    "PythonInteractiveHandler",
]
