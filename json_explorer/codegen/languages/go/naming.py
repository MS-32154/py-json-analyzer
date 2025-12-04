"""
Go-specific naming utilities.

Provides Go reserved words, builtin types, and pre-configured name tracker.
"""

from ...core.naming import NameTracker

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Go Language Keywords and Builtins
# ============================================================================


GO_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        # Keywords
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
)


GO_BUILTIN_TYPES: frozenset[str] = frozenset(
    {
        # Basic types
        "bool",
        "byte",
        "rune",
        "string",
        "int",
        "int8",
        "int16",
        "int32",
        "int64",
        "uint",
        "uint8",
        "uint16",
        "uint32",
        "uint64",
        "uintptr",
        "float32",
        "float64",
        "complex64",
        "complex128",
        "error",
        # Builtin functions
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
)


def create_go_name_tracker() -> NameTracker:
    """
    Create a name tracker configured for Go.

    Returns:
        NameTracker with Go reserved words and builtins
    """
    reserved = GO_RESERVED_WORDS | GO_BUILTIN_TYPES
    tracker = NameTracker(reserved)
    logger.debug(f"Created Go name tracker with {len(reserved)} reserved words")
    return tracker
