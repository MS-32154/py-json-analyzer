"""TypeScript identifier and property-key rules."""

import json
import re

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

_PLAIN_KEY = re.compile(r"[A-Za-z_$][A-Za-z0-9_$]*")


def ts_type_name(name: str) -> str:
    """PascalCase type name: ``user_address`` -> ``UserAddress``."""
    ident = "".join(c for c in to_pascal_case(name) if ("A" + c).isidentifier())
    if not ident:
        return "Type"
    if not ident[0].isalpha():
        ident = "Type" + ident
    return ident + "_" if ident in GLOBAL_TYPES else ident


def property_key(key: str) -> str:
    """A JSON key as a property name: bare if it's an identifier, else quoted."""
    return key if _PLAIN_KEY.fullmatch(key) else js_string(key)


def js_string(text: str) -> str:
    """String literal quoted the way Prettier formats it.

    Double quotes unless the text contains a double quote and no single one.
    """
    escaped = json.dumps(text, ensure_ascii=False)[1:-1]  # JSON escapes are valid JS
    if '"' in text and "'" not in text:
        return "'" + escaped.replace('\\"', '"') + "'"
    return '"' + escaped + '"'
