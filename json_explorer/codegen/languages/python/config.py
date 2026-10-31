"""Python-specific configuration and type mapping."""

from dataclasses import dataclass, field
from enum import Enum

from ...core.schema import FieldType


class PythonStyle(Enum):
    """Python code generation styles."""

    DATACLASS = "dataclass"
    PYDANTIC = "pydantic"
    TYPEDDICT = "typeddict"


# Import statements for types used in annotations
# Module each annotation name is imported from
PYTHON_IMPORTS: dict[str, str] = {
    "datetime": "datetime",
    "date": "datetime",
    "time": "datetime",
    "timedelta": "datetime",
    "Any": "typing",
    "NotRequired": "typing",
}

# Imports every file of a style needs
STYLE_IMPORTS: dict[PythonStyle, list[str]] = {
    PythonStyle.DATACLASS: ["from dataclasses import dataclass"],
    PythonStyle.PYDANTIC: ["from pydantic import BaseModel, Field, ConfigDict"],
    PythonStyle.TYPEDDICT: ["from typing import TypedDict"],
}


_PYDANTIC_FORMATS = {
    FieldType.DATE_TIME: "datetime",
    FieldType.LOCAL_DATE_TIME: "datetime",
    FieldType.DATE: "date",
    FieldType.TIME: "time",
    FieldType.DURATION: "timedelta",
}


@dataclass(slots=True, kw_only=True)
class PythonConfig:
    """Python-specific options.

    Attributes:
        style: dataclass, pydantic or typeddict.
        dataclass_frozen: Make dataclasses immutable.
        dataclass_slots: Use ``__slots__``.
        dataclass_kw_only: Keyword-only constructor arguments.
        pydantic_config_dict: Emit ``model_config`` (populate_by_name, extra).
        pydantic_extra_forbid: Reject unknown keys instead of ignoring them.
    """

    style: PythonStyle = PythonStyle.DATACLASS

    dataclass_frozen: bool = False
    dataclass_slots: bool = True
    dataclass_kw_only: bool = True

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
            # Only Pydantic parses values; dataclasses and TypedDicts hold the
            # JSON string as-is, so a datetime annotation there would be wrong.
            **{
                field_type: annotation if self.style == PythonStyle.PYDANTIC else "str"
                for field_type, annotation in _PYDANTIC_FORMATS.items()
            },
            FieldType.UNKNOWN: "Any",
            FieldType.CONFLICT: "Any",
        }

    def to_dict(self) -> dict:
        return {
            "style": self.style.value,
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
