"""
Language-specific code generators.

This module contains generators for different programming languages.
"""

# Available language modules
__all__ = []

# Import available generators
try:
    from .go import (
        GoGenerator,
        create_go_generator,
        create_web_api_generator,
        create_strict_generator,
    )

    __all__.extend(
        [
            "GoGenerator",
            "create_go_generator",
            "create_web_api_generator",
            "create_strict_generator",
        ]
    )
except ImportError as e:
    # Go generator not available
    pass
except Exception as e:
    # Other errors during import
    import sys

    print(f"Warning: Failed to import Go generator: {e}", file=sys.stderr)

# Python generators
try:
    from .python import (
        PythonGenerator,
        create_python_generator,
        create_dataclass_generator,
        create_pydantic_generator,
        create_typeddict_generator,
    )

    __all__.extend(
        [
            "PythonGenerator",
            "create_python_generator",
            "create_dataclass_generator",
            "create_pydantic_generator",
            "create_typeddict_generator",
        ]
    )
except ImportError as e:
    # Python generator not available - this is expected if not installed yet
    pass
except Exception as e:
    # Other errors during import
    import sys

    print(f"Warning: Failed to import Python generator: {e}", file=sys.stderr)

# Add more languages here as they are implemented
# try:
#     from .python import PythonGenerator
#     __all__.append("PythonGenerator")
# except ImportError:
#     pass
