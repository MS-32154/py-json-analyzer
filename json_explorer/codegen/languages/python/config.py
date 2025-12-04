"""
Python-specific configuration and type mappings.
"""

import re
from dataclasses import dataclass, field
from enum import Enum

from ...core.schema import FieldType

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Python Styles
# ============================================================================


class PythonStyle(Enum):
    """Python code generation styles."""

    DATACLASS = "dataclass"
    PYDANTIC = "pydantic"
    TYPEDDICT = "typeddict"


# ============================================================================
# Type Mappings
# ============================================================================


PYTHON_TYPE_MAP: dict[FieldType, str] = {
    FieldType.STRING: "str",
    FieldType.INTEGER: "int",
    FieldType.FLOAT: "float",
    FieldType.BOOLEAN: "bool",
    FieldType.TIMESTAMP: "datetime",
    FieldType.UNKNOWN: "Any",
    FieldType.CONFLICT: "Any",
}


# Import statements for types
PYTHON_IMPORTS: dict[str, str] = {
    "datetime": "from datetime import datetime",
    "Any": "from typing import Any",
    "List": "from typing import List",
    "Dict": "from typing import Dict",
}


# Style-specific imports
STYLE_IMPORTS: dict[PythonStyle, dict[str, str]] = {
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


# ============================================================================
# Python-Specific Configuration
# ============================================================================


@dataclass(slots=True, kw_only=True)
class PythonConfig:
    """
    Python-specific configuration options.

    Attributes:
        style: Code generation style (dataclass, pydantic, typeddict)
        use_optional: Use type unions (T | None) for optional fields

        Dataclass options:
        dataclass_frozen: Make dataclasses immutable
        dataclass_slots: Use __slots__ for memory optimization
        dataclass_kw_only: Require keyword-only arguments

        Pydantic options:
        pydantic_use_field: Use Field() for metadata
        pydantic_use_alias: Generate field aliases for JSON keys
        pydantic_config_dict: Generate model_config
        pydantic_extra_forbid: Forbid extra fields

        TypedDict options:
        typeddict_total: Make all fields required by default
    """

    # Style selection
    style: PythonStyle = PythonStyle.DATACLASS

    # Type preferences
    int_type: str = "int"
    float_type: str = "float"
    string_type: str = "str"
    bool_type: str = "bool"
    datetime_type: str = "datetime"
    unknown_type: str = "Any"

    # Optional field handling
    use_optional: bool = True

    # Dataclass-specific
    dataclass_frozen: bool = False
    dataclass_slots: bool = True
    dataclass_kw_only: bool = False

    # Pydantic-specific
    pydantic_use_field: bool = True
    pydantic_use_alias: bool = True
    pydantic_config_dict: bool = True
    pydantic_extra_forbid: bool = False

    # TypedDict-specific
    typeddict_total: bool = False

    # Declaration
    type_map: dict = field(init=False, repr=False, default_factory=dict)

    def __post_init__(self) -> None:
        """Initialize type map and validate style."""
        # Convert string style to enum if needed
        if isinstance(self.style, str):
            object.__setattr__(self, "style", PythonStyle(self.style))

        # Build type map
        type_map = PYTHON_TYPE_MAP.copy()
        type_map[FieldType.INTEGER] = self.int_type
        type_map[FieldType.FLOAT] = self.float_type
        type_map[FieldType.STRING] = self.string_type
        type_map[FieldType.BOOLEAN] = self.bool_type
        type_map[FieldType.TIMESTAMP] = self.datetime_type
        type_map[FieldType.UNKNOWN] = self.unknown_type
        type_map[FieldType.CONFLICT] = self.unknown_type

        object.__setattr__(self, "type_map", type_map)

        logger.debug(
            f"PythonConfig initialized: style={self.style.value}, "
            f"optional={self.use_optional}"
        )

    def to_dict(self) -> dict:
        """Convert to dict, excluding computed fields."""
        return {
            "style": (
                self.style.value if isinstance(self.style, PythonStyle) else self.style
            ),
            "int_type": self.int_type,
            "float_type": self.float_type,
            "string_type": self.string_type,
            "bool_type": self.bool_type,
            "datetime_type": self.datetime_type,
            "unknown_type": self.unknown_type,
            "use_optional": self.use_optional,
            "dataclass_frozen": self.dataclass_frozen,
            "dataclass_slots": self.dataclass_slots,
            "dataclass_kw_only": self.dataclass_kw_only,
            "pydantic_use_field": self.pydantic_use_field,
            "pydantic_use_alias": self.pydantic_use_alias,
            "pydantic_config_dict": self.pydantic_config_dict,
            "pydantic_extra_forbid": self.pydantic_extra_forbid,
            "typeddict_total": self.typeddict_total,
        }

    def get_python_type(
        self,
        field_type: FieldType,
        *,
        is_optional: bool = False,
        is_array: bool = False,
        element_type: str | None = None,
    ) -> str:
        """
        Get Python type string for a field.

        Args:
            field_type: Field type enum
            is_optional: Whether field is optional
            is_array: Whether field is an array
            element_type: For arrays, the element type string

        Returns:
            Python type string (e.g., "str", "list[int]", "str | None")
        """
        if is_array:
            base = element_type or self.type_map.get(field_type, self.unknown_type)
            python_type = f"list[{base}]"
        else:
            python_type = self.type_map.get(field_type, self.unknown_type)

        # Add optional wrapper if needed
        if is_optional and self.use_optional:
            match self.style:
                case PythonStyle.TYPEDDICT:
                    return f"NotRequired[{python_type}]"
                case _:
                    return f"{python_type} | None"

        return python_type

    def get_required_imports(
        self,
        types_used: set[str],
        has_optional: bool = False,
    ) -> list[str]:
        """
        Get required imports for the given types.

        Args:
            types_used: Set of Python types used in generated code
            has_optional: Whether any optional fields exist

        Returns:
            Sorted list of import statements
        """
        imports = set()

        # Extract base types from type strings
        for python_type in types_used:
            base_types = self._extract_base_types(python_type)
            for base_type in base_types:
                if base_type in PYTHON_IMPORTS:
                    imports.add(PYTHON_IMPORTS[base_type])

        # Add style-specific imports
        style_imports = STYLE_IMPORTS.get(self.style, {})
        for import_stmt in style_imports.values():
            imports.add(import_stmt)

        # Add NotRequired for TypedDict with optional fields
        if has_optional and self.use_optional:
            if self.style == PythonStyle.TYPEDDICT:
                imports.add(
                    PYTHON_IMPORTS.get("NotRequired", "from typing import NotRequired")
                )

        # Sort: standard library first, then third-party
        sorted_imports = sorted(
            imports,
            key=lambda x: (
                (
                    0
                    if x.startswith("from typing") or x.startswith("from datetime")
                    else 1
                ),
                x,
            ),
        )

        logger.debug(f"Required imports: {len(sorted_imports)}")
        return sorted_imports

    def _extract_base_types(self, type_string: str) -> set[str]:
        """Extract base types from complex type strings like 'list[User]' or 'str | None'."""
        # Find all capitalized identifiers (type names)
        matches = re.findall(r"\b([A-Z][a-zA-Z0-9_]*)\b", type_string)
        return set(matches)


# ============================================================================
# Preset Configurations
# ============================================================================
def get_python_generator_config(**overrides) -> dict:
    """
    Get GeneratorConfig dict with Python-friendly defaults.

    Python conventions:
    - Classes: PascalCase (struct_case="pascal")
    - Fields: snake_case (field_case="snake")
    """
    defaults = {
        "package_name": "models",
        "struct_case": "pascal",
        "field_case": "snake",  # Python convention
        "add_comments": True,
    }
    defaults.update(overrides)
    return defaults


def get_dataclass_config() -> PythonConfig:
    """Configuration for dataclass generation."""
    return PythonConfig(
        style=PythonStyle.DATACLASS,
        dataclass_slots=True,
        dataclass_frozen=False,
        use_optional=True,
    )


def get_pydantic_config() -> PythonConfig:
    """Configuration for Pydantic v2 model generation."""
    return PythonConfig(
        style=PythonStyle.PYDANTIC,
        pydantic_use_field=True,
        pydantic_use_alias=True,
        pydantic_config_dict=True,
        use_optional=True,
    )


def get_typeddict_config() -> PythonConfig:
    """Configuration for TypedDict generation."""
    return PythonConfig(
        style=PythonStyle.TYPEDDICT,
        typeddict_total=False,
        use_optional=True,
    )


def get_strict_dataclass_config() -> PythonConfig:
    """Configuration for strict/frozen dataclass generation."""
    return PythonConfig(
        style=PythonStyle.DATACLASS,
        dataclass_slots=True,
        dataclass_frozen=True,
        dataclass_kw_only=True,
        use_optional=True,
    )
