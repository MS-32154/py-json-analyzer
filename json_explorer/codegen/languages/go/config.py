"""Go-specific configuration and type mapping."""

from dataclasses import dataclass, field
from typing import Literal

from ...core.schema import FieldType

# Unknown and conflicting values (Go 1.18+).
UNKNOWN_TYPE = "any"


@dataclass(slots=True, kw_only=True)
class GoConfig:
    """Go-specific options.

    Attributes:
        int_type: Go type for JSON integers.
        float_type: Go type for JSON floats.
        time_type: Go type for RFC 3339 date-times (``string`` keeps them as text).
        use_pointers_for_optional: Use ``*T`` for optional fields so a
            missing value can be told apart from the zero value.
    """

    int_type: Literal["int", "int32", "int64"] = "int64"
    float_type: Literal["float32", "float64"] = "float64"
    time_type: Literal["time.Time", "string"] = "time.Time"
    use_pointers_for_optional: bool = True

    type_map: dict[FieldType, str] = field(init=False, repr=False)

    def __post_init__(self) -> None:
        self.type_map = {
            FieldType.STRING: "string",
            FieldType.INTEGER: self.int_type,
            FieldType.FLOAT: self.float_type,
            FieldType.BOOLEAN: "bool",
            # encoding/json decodes RFC 3339 date-times into time.Time; it has
            # no types for the other formats, so they stay strings.
            FieldType.DATE_TIME: self.time_type,
            FieldType.LOCAL_DATE_TIME: "string",
            FieldType.DATE: "string",
            FieldType.TIME: "string",
            FieldType.DURATION: "string",
            FieldType.UNKNOWN: UNKNOWN_TYPE,
            FieldType.CONFLICT: UNKNOWN_TYPE,
        }

    def to_dict(self) -> dict:
        return {
            "int_type": self.int_type,
            "float_type": self.float_type,
            "time_type": self.time_type,
            "use_pointers_for_optional": self.use_pointers_for_optional,
        }

    def get_go_type(self, field_type: FieldType, *, is_optional: bool = False) -> str:
        """Go type for a primitive field, e.g. ``string`` or ``*int64``."""
        go_type = self.type_map.get(field_type, UNKNOWN_TYPE)
        # Pointers only where they add information (never for any or slices)
        if is_optional and self.use_pointers_for_optional and go_type != UNKNOWN_TYPE:
            return f"*{go_type}"
        return go_type
