"""Rust identifier and string-literal rules."""

from ...core.naming import to_pascal_case, to_snake_case

# Strict and reserved keywords (2024 edition). They can be used as raw
# identifiers (r#type), except the ones listed in NOT_RAW.
KEYWORDS = frozenset(
    {
        "abstract", "as", "async", "await", "become", "box", "break", "const",
        "continue", "crate", "do", "dyn", "else", "enum", "extern", "false",
        "final", "fn", "for", "gen", "if", "impl", "in", "let", "loop", "macro",
        "match", "mod", "move", "mut", "override", "priv", "pub", "ref",
        "return", "self", "static", "struct", "super", "trait", "true", "try",
        "type", "typeof", "unsafe", "unsized", "use", "virtual", "where",
        "while", "yield",
    }
)  # fmt: skip
NOT_RAW = frozenset({"self", "super", "crate", "_"})

# Types the generated code uses or that are always in scope.
RESERVED_TYPES = frozenset(
    {"Box", "Option", "Result", "Self", "String", "Value", "Vec", "Map"}
)


def rust_type_name(name: str) -> str:
    """ASCII PascalCase type name: ``user_address`` -> ``UserAddress``."""
    ident = "".join(c for c in to_pascal_case(name) if c.isascii())
    if not ident:
        return "Type"
    if not ident[0].isalpha():
        ident = "Type" + ident
    return ident + "Type" if ident in RESERVED_TYPES else ident


def rust_field_name(key: str) -> str:
    """ASCII snake_case field name: ``userId`` -> ``user_id``; ``type`` -> ``r#type``."""
    ident = "".join(c for c in to_snake_case(key) if c.isascii()).strip("_")
    if not ident:
        return "field"
    if not ident[0].isalpha():
        ident = "field_" + ident
    if ident in NOT_RAW:
        return ident + "_"
    return f"r#{ident}" if ident in KEYWORDS else ident


def rust_string(text: str) -> str:
    """A Rust string literal."""
    out = []
    for char in text:
        match char:
            case "\\" | '"':
                out.append("\\" + char)
            case "\n":
                out.append("\\n")
            case "\r":
                out.append("\\r")
            case "\t":
                out.append("\\t")
            case _ if ord(char) < 0x20 or ord(char) == 0x7F:
                out.append(f"\\u{{{ord(char):x}}}")
            case _:
                out.append(char)
    return '"' + "".join(out) + '"'
