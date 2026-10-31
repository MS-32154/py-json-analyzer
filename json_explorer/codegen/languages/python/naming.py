"""Python identifier rules for generated classes and fields.

Builtins such as ``id`` or ``type`` are fine as attribute names and are kept.
Only names that would break the generated module are changed (with a
trailing underscore): keywords, names used in the generated annotations and
imports, and attributes Pydantic reserves on ``BaseModel``.
"""

import keyword

from ...core.naming import to_pascal_case, to_snake_case

# Names the generated code imports or uses in annotations. A class or a
# field with a default named like one of them would shadow it in the class
# namespace (annotations are evaluated there).
GENERATED_NAMES = frozenset(
    {
        "Any",
        "BaseModel",
        "ConfigDict",
        "Field",
        "NotRequired",
        "TypedDict",
        "bool",
        "dataclass",
        "dict",
        "field",
        "float",
        "int",
        "list",
        "str",
    }
)

# BaseModel attributes a field must not shadow (Pydantic v2), and the
# datetime names Pydantic models import for date/time fields.
PYDANTIC_RESERVED = frozenset(
    {
        "date",
        "datetime",
        "time",
        "timedelta",
        "construct",
        "copy",
        "dict",
        "from_orm",
        "json",
        "parse_file",
        "parse_obj",
        "parse_raw",
        "schema",
        "schema_json",
        "update_forward_refs",
        "validate",
    }
)


def _avoid_reserved(ident: str, reserved: frozenset[str]) -> str:
    if keyword.iskeyword(ident) or ident in reserved:
        return ident + "_"
    return ident


def _valid_chars(ident: str) -> str:
    # str.isalnum() accepts some characters identifiers don't (e.g. "²").
    return "".join(c if ("a" + c).isidentifier() else "_" for c in ident)


def python_class_name(name: str) -> str:
    """``user_address`` -> ``UserAddress``; ``123`` -> ``Model123``."""
    ident = _valid_chars(to_pascal_case(name)) or "Model"
    if not ident[0].isalpha():
        ident = "Model" + ident
    return _avoid_reserved(ident, GENERATED_NAMES)


def python_field_name(key: str, *, pydantic: bool = False) -> str:
    """``userName`` -> ``user_name``; ``123abc`` -> ``field_123abc``; ``class`` -> ``class_``.

    Never starts with an underscore: Pydantic treats such names as private.
    """
    ident = _valid_chars(to_snake_case(key)).strip("_") or "field"
    if not ident[0].isalpha():
        ident = "field_" + ident
    reserved = GENERATED_NAMES | PYDANTIC_RESERVED if pydantic else GENERATED_NAMES
    if pydantic and ident.startswith("model_"):
        ident = "field_" + ident  # Pydantic's protected namespace
    return _avoid_reserved(ident, reserved)


def is_plain_key(key: str) -> bool:
    """Whether a JSON key can be a field name in class-syntax TypedDict."""
    return key.isidentifier() and not keyword.iskeyword(key)
