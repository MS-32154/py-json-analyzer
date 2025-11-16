"""
Python-specific naming utilities and sanitization.

Handles Python reserved words, builtins, and naming conventions.
"""

from ...core.naming import NameSanitizer


# Python reserved keywords
PYTHON_RESERVED_WORDS = {
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
}

# Python built-in types and functions
PYTHON_BUILTIN_TYPES = {
    # Types
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
    "frozenset",
    "range",
    "object",
    "type",
    "complex",
    "memoryview",
    # Special attributes
    "property",
    "staticmethod",
    "classmethod",
    "super",
    # Common functions
    "len",
    "print",
    "input",
    "open",
    "all",
    "any",
    "abs",
    "min",
    "max",
    "sum",
    "sorted",
    "reversed",
    "enumerate",
    "zip",
    "map",
    "filter",
    "isinstance",
    "issubclass",
    "hasattr",
    "getattr",
    "setattr",
    "delattr",
    "dir",
    "vars",
    "id",
    "hash",
    "repr",
    "str",
    "format",
    "iter",
    "next",
    "slice",
    "callable",
    # Exceptions
    "Exception",
    "BaseException",
    "ValueError",
    "TypeError",
    "KeyError",
    "AttributeError",
    "IndexError",
    "RuntimeError",
    "NotImplementedError",
    "StopIteration",
}


def create_python_sanitizer() -> NameSanitizer:
    """Create a name sanitizer configured for Python."""
    return NameSanitizer(PYTHON_RESERVED_WORDS, PYTHON_BUILTIN_TYPES)
