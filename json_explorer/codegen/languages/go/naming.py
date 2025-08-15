"""
Go-specific naming utilities and sanitization.

Handles Go reserved words, builtins, and naming conventions.
"""

from ...core.naming import NameSanitizer, NamingCase


# Go reserved words
GO_RESERVED_WORDS = {
    "break",
    "case",
    "chan",
    "const",
    "continue",
    "default",
    "defer",
    "else",
    "fallthrough",
    "for",
    "func",
    "go",
    "goto",
    "if",
    "import",
    "interface",
    "map",
    "package",
    "range",
    "return",
    "select",
    "struct",
    "switch",
    "type",
    "var",
}

# Go builtin types and functions
GO_BUILTIN_TYPES = {
    "bool",
    "byte",
    "complex64",
    "complex128",
    "error",
    "float32",
    "float64",
    "int",
    "int8",
    "int16",
    "int32",
    "int64",
    "rune",
    "string",
    "uint",
    "uint8",
    "uint16",
    "uint32",
    "uint64",
    "uintptr",
    "append",
    "cap",
    "close",
    "complex",
    "copy",
    "delete",
    "imag",
    "len",
    "make",
    "new",
    "panic",
    "print",
    "println",
    "real",
    "recover",
}


def create_go_sanitizer() -> NameSanitizer:
    """Create a name sanitizer configured for Go."""
    return NameSanitizer(GO_RESERVED_WORDS, GO_BUILTIN_TYPES)


def validate_go_package_name(name: str) -> list[str]:
    """
    (NOT USED YET)
    Validate Go package name according to Go naming rules.

    Returns:
        List of validation errors (empty if valid)
    """
    errors = []

    if not name:
        errors.append("Package name cannot be empty")
        return errors

    # Check basic identifier rules
    if not name.isidentifier():
        errors.append(f"'{name}' is not a valid Go identifier")

    # Go-specific rules
    if name[0].isupper():
        errors.append("Package names should be lowercase")

    if "_" in name:
        errors.append("Package names should not contain underscores")

    if "-" in name:
        errors.append("Package names should not contain hyphens")

    # Check against reserved words
    if name.lower() in GO_RESERVED_WORDS:
        errors.append(f"'{name}' is a Go reserved word")

    return errors
