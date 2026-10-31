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
from .naming import python_class_name, python_field_name

__all__ = [
    "PythonConfig",
    "PythonGenerator",
    "PythonInteractiveHandler",
    "PythonStyle",
    "create_dataclass_generator",
    "create_pydantic_generator",
    "create_python_generator",
    "create_typeddict_generator",
    "get_dataclass_config",
    "get_pydantic_config",
    "get_strict_dataclass_config",
    "get_typeddict_config",
    "python_class_name",
    "python_field_name",
]
