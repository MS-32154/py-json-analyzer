"""
Python-specific configuration and type mappings.

Provides type mapping and Python-specific configuration for
dataclasses, Pydantic models, and TypedDict generation.
"""

from typing import Set
from enum import Enum
from ...core.schema import FieldType
from .naming import PYTHON_BUILTIN_TYPES, PYTHON_RESERVED_WORDS


class PythonStyle(Enum):
    """Python code generation styles."""

    DATACLASS = "dataclass"
    PYDANTIC = "pydantic"
    TYPEDDICT = "typeddict"


# Python type mappings
PYTHON_TYPE_MAP = {
    FieldType.STRING: "str",
    FieldType.INTEGER: "int",
    FieldType.FLOAT: "float",
    FieldType.BOOLEAN: "bool",
    FieldType.TIMESTAMP: "datetime",
    FieldType.UNKNOWN: "Any",
    FieldType.CONFLICT: "Any",
}

# Types that require imports
PYTHON_IMPORT_MAP = {
    "datetime": "from datetime import datetime",
    "Any": "from typing import Any",
    "Optional": "from typing import Optional",
    "List": "from typing import List",
    "Dict": "from typing import Dict",
    "Union": "from typing import Union",
}

# Additional imports by style
STYLE_IMPORTS = {
    PythonStyle.DATACLASS: {
        "dataclass": "from dataclasses import dataclass, field",
    },
    PythonStyle.PYDANTIC: {
        "BaseModel": "from pydantic import BaseModel, Field, ConfigDict",
    },
    PythonStyle.TYPEDDICT: {
        "TypedDict": "from typing import TypedDict",
        "NotRequired": "from typing import NotRequired",  # Python 3.11+
    },
}


class PythonConfig:
    """Python-specific configuration."""

    def __init__(self, **kwargs):
        """Initialize Python configuration."""
        # Style selection
        style_str = kwargs.get("style", "dataclass")
        if isinstance(style_str, PythonStyle):
            self.style = style_str
        else:
            try:
                self.style = PythonStyle(style_str)
            except ValueError:
                self.style = PythonStyle.DATACLASS

        # Type preferences
        self.int_type = kwargs.get("int_type", "int")
        self.float_type = kwargs.get("float_type", "float")
        self.string_type = kwargs.get("string_type", "str")
        self.bool_type = kwargs.get("bool_type", "bool")
        self.datetime_type = kwargs.get("datetime_type", "datetime")
        self.unknown_type = kwargs.get("unknown_type", "Any")

        # Optional field handling
        self.use_optional = kwargs.get("use_optional", True)

        # Pydantic-specific options
        self.pydantic_use_field = kwargs.get("pydantic_use_field", True)
        self.pydantic_use_alias = kwargs.get("pydantic_use_alias", True)
        self.pydantic_config_dict = kwargs.get("pydantic_config_dict", True)
        self.pydantic_extra_forbid = kwargs.get("pydantic_extra_forbid", False)

        # Dataclass-specific options
        self.dataclass_frozen = kwargs.get("dataclass_frozen", False)
        self.dataclass_slots = kwargs.get("dataclass_slots", True)  # Python 3.10+
        self.dataclass_kw_only = kwargs.get("dataclass_kw_only", False)  # Python 3.10+

        # TypedDict-specific options
        self.typeddict_total = kwargs.get(
            "typeddict_total", False
        )  # Default to all optional

        # Field naming
        self.preserve_field_names = kwargs.get("preserve_field_names", True)

        # Build type map with configured types
        self.type_map = PYTHON_TYPE_MAP.copy()
        self.type_map[FieldType.INTEGER] = self.int_type
        self.type_map[FieldType.FLOAT] = self.float_type
        self.type_map[FieldType.STRING] = self.string_type
        self.type_map[FieldType.BOOLEAN] = self.bool_type
        self.type_map[FieldType.TIMESTAMP] = self.datetime_type
        self.type_map[FieldType.UNKNOWN] = self.unknown_type
        self.type_map[FieldType.CONFLICT] = self.unknown_type

    def get_python_type(
        self,
        field_type: FieldType,
        is_optional: bool = False,
        is_array: bool = False,
        element_type: str = None,
    ) -> str:
        """Get Python type string for a field type."""
        if is_array:
            if element_type:
                base_type = element_type
            else:
                base_type = self.type_map.get(field_type, self.unknown_type)

            python_type = f"list[{base_type}]"
        else:
            python_type = self.type_map.get(field_type, self.unknown_type)

        # Add Optional for optional fields if configured
        if is_optional and self.use_optional:
            # For TypedDict, use NotRequired instead of Optional
            if self.style == PythonStyle.TYPEDDICT:
                python_type = f"NotRequired[{python_type}]"
            else:
                python_type = f"{python_type} | None"

        return python_type

    def get_required_imports(
        self, types_used: Set[str], has_optional: bool = False
    ) -> Set[str]:
        """Get required imports for the given types."""
        imports = set()

        # Check for standard type imports
        for python_type in types_used:
            # Check base types (remove list[], Optional[], etc.)
            base_types = self._extract_base_types(python_type)

            for base_type in base_types:
                if base_type in PYTHON_IMPORT_MAP:
                    imports.add(PYTHON_IMPORT_MAP[base_type])

        # Add style-specific imports
        style_imports = STYLE_IMPORTS.get(self.style, {})
        for import_stmt in style_imports.values():
            imports.add(import_stmt)

        # Add Optional/NotRequired if needed
        if has_optional and self.use_optional:
            if self.style == PythonStyle.TYPEDDICT:
                imports.add(PYTHON_IMPORT_MAP["NotRequired"])
            # Optional is included via Union in modern Python (|)

        return imports

    def _extract_base_types(self, type_string: str) -> Set[str]:
        """Extract base types from complex type strings."""
        base_types = set()

        # Remove list[], Optional[], NotRequired[], etc.
        import re

        # Find all identifiers that could be types
        matches = re.findall(r"\b([A-Z][a-zA-Z0-9_]*)\b", type_string)
        base_types.update(matches)

        return base_types


def get_python_reserved_words() -> Set[str]:
    """Get Python reserved words."""
    return PYTHON_RESERVED_WORDS


def get_python_builtin_types() -> Set[str]:
    """Get Python builtin types."""
    return PYTHON_BUILTIN_TYPES


# Default configurations for different styles
def get_dataclass_config() -> PythonConfig:
    """Configuration for dataclass generation."""
    return PythonConfig(
        style="dataclass",
        dataclass_slots=True,
        dataclass_frozen=False,
        use_optional=True,
    )


def get_pydantic_config() -> PythonConfig:
    """Configuration for Pydantic v2 model generation."""
    return PythonConfig(
        style="pydantic",
        pydantic_use_field=True,
        pydantic_use_alias=True,
        pydantic_config_dict=True,
        use_optional=True,
    )


def get_typeddict_config() -> PythonConfig:
    """Configuration for TypedDict generation."""
    return PythonConfig(
        style="typeddict",
        typeddict_total=False,  # Allow optional fields by default
        use_optional=True,
    )


def get_strict_dataclass_config() -> PythonConfig:
    """Configuration for strict/frozen dataclass generation."""
    return PythonConfig(
        style="dataclass",
        dataclass_slots=True,
        dataclass_frozen=True,
        dataclass_kw_only=True,
        use_optional=True,
    )
