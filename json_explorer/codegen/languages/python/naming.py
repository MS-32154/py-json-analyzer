"""
Python-specific naming utilities.

Provides Python reserved words, builtin types, and pre-configured name tracker.
"""

from ...core.naming import NameTracker

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Python Language Keywords and Builtins
# ============================================================================


PYTHON_RESERVED_WORDS: frozenset[str] = frozenset(
    {
        # Keywords
        "False",
        "None",
        "True",
        "and",
        "as",
        "assert",
        "async",
        "await",
        "break",
        "class",
        "continue",
        "def",
        "del",
        "elif",
        "else",
        "except",
        "finally",
        "for",
        "from",
        "global",
        "if",
        "import",
        "in",
        "is",
        "lambda",
        "nonlocal",
        "not",
        "or",
        "pass",
        "raise",
        "return",
        "try",
        "while",
        "with",
        "yield",
        # Soft keywords (context-dependent, but safer to avoid)
        "match",
        "case",
        "_",
    }
)


PYTHON_BUILTIN_TYPES: frozenset[str] = frozenset(
    {
        # Basic types
        "int",
        "float",
        "str",
        "bool",
        "list",
        "dict",
        "set",
        "tuple",
        "bytes",
        "bytearray",
        "complex",
        "frozenset",
        "range",
        "object",
        "type",
        # Special
        "super",
        "property",
        "staticmethod",
        "classmethod",
        # Builtin functions
        "abs",
        "all",
        "any",
        "ascii",
        "bin",
        "breakpoint",
        "callable",
        "chr",
        "compile",
        "delattr",
        "dir",
        "divmod",
        "enumerate",
        "eval",
        "exec",
        "filter",
        "format",
        "getattr",
        "globals",
        "hasattr",
        "hash",
        "help",
        "hex",
        "id",
        "input",
        "isinstance",
        "issubclass",
        "iter",
        "len",
        "locals",
        "map",
        "max",
        "memoryview",
        "min",
        "next",
        "oct",
        "open",
        "ord",
        "pow",
        "print",
        "repr",
        "reversed",
        "round",
        "setattr",
        "slice",
        "sorted",
        "sum",
        "vars",
        "zip",
        # Common module names to avoid
        "datetime",
        "json",
        "typing",
        "dataclasses",
        "pydantic",
    }
)


def create_python_name_tracker() -> NameTracker:
    """
    Create a name tracker configured for Python.

    Returns:
        NameTracker with Python reserved words and builtins
    """
    reserved = PYTHON_RESERVED_WORDS | PYTHON_BUILTIN_TYPES
    tracker = NameTracker(reserved)
    logger.debug(f"Created Python name tracker with {len(reserved)} reserved words")
    return tracker
