"""JSON structure analysis.

``analyze_json`` describes the shape of a JSON document as a tree of
:class:`Node` objects: one node per position, merged over every value seen
there (every array element is used, not a sample). Merging is a single rule:

- the same kind merges recursively (object fields, array items);
- ``null`` or a key missing from some objects makes the node *optional*;
- integers and floats merge to float;
- anything else becomes ``mixed``, recording the kinds seen.

Strings that all follow one standard date/time format (RFC 3339, as used by
JSON Schema's ``format``) carry that :class:`Format`.
"""

import datetime as dt
import re
from dataclasses import dataclass, field, replace
from enum import StrEnum
from typing import Any

from .logging_config import get_logger

logger = get_logger(__name__)


class Kind(StrEnum):
    """JSON value kinds (integers and floats kept apart)."""

    OBJECT = "object"
    ARRAY = "array"
    STRING = "string"
    INTEGER = "integer"
    FLOAT = "float"
    BOOLEAN = "boolean"
    NULL = "null"
    MIXED = "mixed"


class Format(StrEnum):
    """Standard string formats (JSON Schema names; RFC 3339 / ISO 8601)."""

    DATE_TIME = "date-time"  # 2024-01-01T10:00:00Z (with offset: RFC 3339)
    LOCAL_DATE_TIME = "local-date-time"  # 2024-01-01T10:00:00 (no offset)
    DATE = "date"  # 2024-01-01
    TIME = "time"  # 10:00:00, 10:00:00Z, 10:00:00.5+02:00
    DURATION = "duration"  # P3D, PT4H30M, P1DT0.5S (days and smaller units)


_SECONDS = r"\d{2}:\d{2}:\d{2}(?:\.\d+)?"
_OFFSET = r"(?:Z|[+-]\d{2}:\d{2})"
# Anchored patterns following RFC 3339's grammar; values are then range-checked.
_PATTERNS: tuple[tuple[Format, re.Pattern[str]], ...] = (
    (Format.DATE_TIME, re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}T{_SECONDS}{_OFFSET}")),
    (Format.LOCAL_DATE_TIME, re.compile(rf"\d{{4}}-\d{{2}}-\d{{2}}T{_SECONDS}")),
    (Format.DATE, re.compile(r"\d{4}-\d{2}-\d{2}")),
    (Format.TIME, re.compile(rf"{_SECONDS}{_OFFSET}?")),
    (
        Format.DURATION,
        re.compile(
            r"P(?=\d|T\d)(?:\d+D)?(?:T(?=\d)(?:\d+H)?(?:\d+M)?(?:\d+(?:\.\d+)?S)?)?"
        ),
    ),
)
_VALIDATORS = {
    Format.DATE_TIME: dt.datetime.fromisoformat,
    Format.LOCAL_DATE_TIME: dt.datetime.fromisoformat,
    Format.DATE: dt.date.fromisoformat,
    Format.TIME: dt.time.fromisoformat,
}


def detect_format(text: str) -> Format | None:
    """The standard format ``text`` follows, if any (``2024-13-45`` is none)."""
    for fmt, pattern in _PATTERNS:
        if pattern.fullmatch(text):
            validate = _VALIDATORS.get(fmt)
            if validate is None:
                return fmt
            try:
                validate(text)
            except ValueError:
                return None
            return fmt
    return None


@dataclass(slots=True, frozen=True)
class Node:
    """The shape of the values found at one position of a JSON document.

    Attributes:
        kind: The value kind (``mixed`` if different kinds were seen).
        optional: Missing from some objects, or ``null`` somewhere.
        fields: For objects: the shape of each key.
        items: For arrays: the merged shape of all elements (``None`` if only
            empty arrays were seen).
        kinds: For ``mixed``: the kinds seen (without ``null``).
        format: For strings: the standard format all values follow, if any.
    """

    kind: Kind
    optional: bool = False
    fields: dict[str, Node] = field(default_factory=dict)
    items: Node | None = None
    kinds: frozenset[Kind] = frozenset()
    format: Format | None = None

    def to_dict(self) -> dict[str, Any]:
        """Plain-dict form (for printing or JSON), omitting empty attributes."""
        result: dict[str, Any] = {"kind": self.kind.value}
        if self.optional:
            result["optional"] = True
        if self.kind == Kind.OBJECT:
            result["fields"] = {k: v.to_dict() for k, v in self.fields.items()}
        if self.kind == Kind.ARRAY:
            result["items"] = self.items.to_dict() if self.items else None
        if self.kinds:
            result["kinds"] = sorted(k.value for k in self.kinds)
        if self.format:
            result["format"] = self.format.value
        return result


def analyze_json(data: Any) -> Node:
    """Describe the structure of JSON data (as returned by ``json.load``).

    Example:
        >>> analyze_json([{"id": 1}, {"id": 2.5, "tag": "x"}]).to_dict()
        {'kind': 'array', 'items': {'kind': 'object', 'fields': {'id': {'kind': 'float'}, 'tag': {'kind': 'string', 'optional': True}}}}
    """
    return _analyze(data)


def _analyze(value: Any) -> Node:
    match value:
        case None:
            return Node(Kind.NULL, optional=True)
        case bool():
            return Node(Kind.BOOLEAN)
        case int():
            return Node(Kind.INTEGER)
        case float():
            return Node(Kind.FLOAT)
        case str():
            return Node(Kind.STRING, format=detect_format(value))
        case dict():
            return Node(Kind.OBJECT, fields={k: _analyze(v) for k, v in value.items()})
        case list() | tuple():
            items: Node | None = None
            for element in value:
                node = _analyze(element)
                items = node if items is None else merge(items, node)
            return Node(Kind.ARRAY, items=items)
        case _:
            raise TypeError(f"Not a JSON value: {type(value).__name__}")


def merge(a: Node, b: Node) -> Node:
    """Shape describing values of both shapes."""
    optional = a.optional or b.optional
    if a.kind == Kind.NULL:
        return replace(b, optional=True)
    if b.kind == Kind.NULL:
        return replace(a, optional=True)

    if a.kind == b.kind:
        match a.kind:
            case Kind.OBJECT:
                fields = {}
                for key in a.fields | b.fields:
                    if key in a.fields and key in b.fields:
                        fields[key] = merge(a.fields[key], b.fields[key])
                    else:  # missing from one of the objects
                        fields[key] = replace(
                            a.fields.get(key) or b.fields[key], optional=True
                        )
                return Node(Kind.OBJECT, optional, fields=fields)
            case Kind.ARRAY:
                if a.items is None or b.items is None:
                    items = a.items or b.items
                else:
                    items = merge(a.items, b.items)
                return Node(Kind.ARRAY, optional, items=items)
            case Kind.MIXED:
                return Node(Kind.MIXED, optional, kinds=a.kinds | b.kinds)
            case Kind.STRING:
                # A format holds only if every value follows it
                fmt = a.format if a.format == b.format else None
                return Node(Kind.STRING, optional, format=fmt)
            case _:
                return Node(a.kind, optional)

    kinds = (a.kinds or {a.kind}) | (b.kinds or {b.kind})
    if Kind.FLOAT in kinds:
        kinds -= {Kind.INTEGER}  # integers widen to float
    if len(kinds) == 1:
        return Node(next(iter(kinds)), optional)
    return Node(Kind.MIXED, optional, kinds=frozenset(kinds))
