"""TypeScript identifier and property-key rules."""

import json

from ...core.naming import to_pascal_case

# Global types a generated type must not shadow: the generated code refers
# to some of them (Record), and shadowing the others is confusing.
GLOBAL_TYPES = frozenset(
    {
        "Array",
        "BigInt",
        "Boolean",
        "Date",
        "Error",
        "Function",
        "JSON",
        "Map",
        "Math",
        "Number",
        "Object",
        "Omit",
        "Partial",
        "Pick",
        "Promise",
        "Readonly",
        "Record",
        "RegExp",
        "Required",
        "Set",
        "String",
        "Symbol",
    }
)


def ts_type_name(name: str) -> str:
    """PascalCase type name: ``user_address`` -> ``UserAddress``."""
    ident = "".join(c for c in to_pascal_case(name) if ("A" + c).isidentifier())
    if not ident:
        return "Type"
    if not ident[0].isalpha():
        ident = "Type" + ident
    return ident + "_" if ident in GLOBAL_TYPES else ident


def is_identifier(key: str) -> bool:
    """Whether a key is a JavaScript identifier (Unicode letters allowed)."""
    return key.replace("$", "_").isidentifier()


def property_key(key: str, *, object_literal: bool = False) -> str:
    """A JSON key as a property name: bare if it's an identifier, else quoted.

    In an object literal (Zod schemas) ``__proto__`` sets the prototype
    instead of creating a key, quoted or not; a computed key avoids that.
    """
    if object_literal and key == "__proto__":
        return '["__proto__"]'
    return key if is_identifier(key) else js_string(key)


def js_string(text: str) -> str:
    """String literal quoted the way Prettier formats it.

    Double quotes unless the text contains a double quote and no single one.
    """
    escaped = json.dumps(text, ensure_ascii=False)[1:-1]  # JSON escapes are valid JS
    if '"' in text and "'" not in text:
        return "'" + escaped.replace('\\"', '"') + "'"
    return '"' + escaped + '"'
