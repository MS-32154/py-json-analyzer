"""Python-specific configuration and type mapping."""

from dataclasses import dataclass, field
from enum import Enum
from typing import Literal

from ...core.schema import FieldType


class PythonStyle(Enum):
    """Python code generation styles."""

    DATACLASS = "dataclass"
    PYDANTIC = "pydantic"
    TYPEDDICT = "typeddict"


# Import statements for types used in annotations
PYTHON_IMPORTS: dict[str, str] = {
    "datetime": "from datetime import datetime",
    "Any": "from typing import Any",
    "NotRequired": "from typing import NotRequired",
}

# Imports every file of a style needs
STYLE_IMPORTS: dict[PythonStyle, list[str]] = {
    PythonStyle.DATACLASS: ["from dataclasses import dataclass"],
    PythonStyle.PYDANTIC: ["from pydantic import BaseModel, Field, ConfigDict"],
    PythonStyle.TYPEDDICT: ["from typing import TypedDict"],
}


@dataclass(slots=True, kw_only=True)
class PythonConfig:
    """Python-specific options.

    Attributes:
        style: dataclass, pydantic or typeddict.
        datetime_type: Annotation for timestamps (``str`` keeps them as text;
            dataclasses and TypedDicts don't parse values).
        dataclass_frozen: Make dataclasses immutable.
        dataclass_slots: Use ``__slots__``.
        dataclass_kw_only: Keyword-only constructor arguments.
        pydantic_config_dict: Emit ``model_config`` (populate_by_name, extra).
        pydantic_extra_forbid: Reject unknown keys instead of ignoring them.
    """

    style: PythonStyle = PythonStyle.DATACLASS
    datetime_type: Literal["datetime", "str"] = "datetime"

    dataclass_frozen: bool = False
    dataclass_slots: bool = True
    dataclass_kw_only: bool = False

    pydantic_config_dict: bool = True
    pydantic_extra_forbid: bool = False

    type_map: dict[FieldType, str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        if isinstance(self.style, str):
            self.style = PythonStyle(self.style)
        self.type_map = {
            FieldType.STRING: "str",
            FieldType.INTEGER: "int",
            FieldType.FLOAT: "float",
            FieldType.BOOLEAN: "bool",
            FieldType.TIMESTAMP: self.datetime_type,
            FieldType.UNKNOWN: "Any",
            FieldType.CONFLICT: "Any",
        }

    def to_dict(self) -> dict:
        return {
            "style": self.style.value,
            "datetime_type": self.datetime_type,
            "dataclass_frozen": self.dataclass_frozen,
            "dataclass_slots": self.dataclass_slots,
            "dataclass_kw_only": self.dataclass_kw_only,
            "pydantic_config_dict": self.pydantic_config_dict,
            "pydantic_extra_forbid": self.pydantic_extra_forbid,
        }

    def optional(self, python_type: str) -> str:
        """Annotation for a field that may be missing or null."""
        if self.style == PythonStyle.TYPEDDICT:
            return f"NotRequired[{python_type}]"
        return f"{python_type} | None"
