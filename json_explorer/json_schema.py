"""Export the inferred structure as JSON Schema (draft 2020-12).

The schema describes the analyzed document as a whole (an array root stays
an array) and only claims what every value showed:

- object keys present in every object are ``required``;
- a value seen as ``null`` allows ``"null"``;
- integers merged with floats are ``"number"``; mixed kinds list every type;
- string formats are emitted where they match JSON Schema's definitions
  (``date-time``, ``date``, ``duration``). Times and date-times without an
  offset, which JSON Schema's ``time``/``date-time`` formats don't allow,
  get a description instead.

Additional properties stay allowed: a sample shows which keys exist, not
which keys may never appear.
"""

from typing import Any

from .analyzer import Format, Kind, Node, analyze_json

DRAFT = "https://json-schema.org/draft/2020-12/schema"

_TYPES = {
    Kind.OBJECT: "object",
    Kind.ARRAY: "array",
    Kind.STRING: "string",
    Kind.INTEGER: "integer",
    Kind.FLOAT: "number",
    Kind.BOOLEAN: "boolean",
    Kind.NULL: "null",
}
_FORMATS = {
    Format.DATE_TIME: "date-time",
    Format.DATE: "date",
    Format.DURATION: "duration",
}
_DESCRIPTIONS = {
    Format.LOCAL_DATE_TIME: "Date-time without a UTC offset (e.g. 2024-01-01T10:00:00)",
    Format.TIME: "Time of day, with or without a UTC offset (e.g. 10:30:00)",
}


def json_schema(data: Any, title: str | None = None) -> dict[str, Any]:
    """JSON Schema for a JSON document (analyzes it first)."""
    return to_json_schema(analyze_json(data), title=title)


def to_json_schema(node: Node, title: str | None = None) -> dict[str, Any]:
    """JSON Schema for the structure ``analyze_json()`` inferred."""
    schema: dict[str, Any] = {"$schema": DRAFT}
    if title:
        schema["title"] = title
    schema.update(_schema(node))
    return schema


def _schema(node: Node | None) -> dict[str, Any]:
    if node is None:  # only empty arrays seen: anything is allowed
        return {}
    if node.kind == Kind.MIXED:
        kinds = sorted({_TYPES[k] for k in node.kinds})
        types = kinds + (["null"] if node.nullable else [])
        return {"type": types}

    schema: dict[str, Any] = {}
    kind_type = _TYPES[node.kind]
    schema["type"] = (
        [kind_type, "null"] if node.nullable and node.kind != Kind.NULL else kind_type
    )

    match node.kind:
        case Kind.OBJECT:
            schema["properties"] = {
                key: _schema(child) for key, child in node.fields.items()
            }
            required = [key for key, child in node.fields.items() if not child.optional]
            if required:
                schema["required"] = required
        case Kind.ARRAY:
            schema["items"] = _schema(node.items)
        case Kind.STRING if node.format in _FORMATS:
            schema["format"] = _FORMATS[node.format]
        case Kind.STRING if node.format in _DESCRIPTIONS:
            schema["description"] = _DESCRIPTIONS[node.format]
    return schema
