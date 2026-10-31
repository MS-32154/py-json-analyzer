"""TypeScript-specific configuration."""

from dataclasses import dataclass
from enum import StrEnum


class TypeScriptStyle(StrEnum):
    """Output styles."""

    INTERFACE = "interface"  # exported interfaces (types only)
    ZOD = "zod"  # Zod schemas (runtime validation) plus inferred types


@dataclass(slots=True, kw_only=True)
class TypeScriptConfig:
    """TypeScript-specific options.

    Attributes:
        style: ``interface`` for plain interfaces, ``zod`` for Zod 4 schemas
            with ``z.infer`` types.
    """

    style: TypeScriptStyle = TypeScriptStyle.INTERFACE

    def __post_init__(self) -> None:
        self.style = TypeScriptStyle(self.style)

    def to_dict(self) -> dict:
        return {"style": self.style.value}
