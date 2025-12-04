"""
Naming utilities for code generation.

Handles name sanitization, case conversions, and conflict resolution
for generating valid identifiers across different programming languages.
"""

import re
from functools import cache
from typing import Literal

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)

# Type aliases for better readability
CaseStyle = Literal["snake", "camel", "pascal", "kebab", "screaming_snake"]


# ============================================================================
# Pure Functions: Case Conversion (Cached)
# ============================================================================


@cache
def to_snake_case(name: str) -> str:
    """
    Convert name to snake_case.

    Examples:
        >>> to_snake_case("UserName")
        'user_name'
        >>> to_snake_case("user-name")
        'user_name'
    """
    # Replace hyphens with underscores
    name = name.replace("-", "_")

    # Insert underscore before uppercase letters
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

    # Convert to lowercase and clean up multiple underscores
    name = name.lower()
    name = re.sub(r"_+", "_", name)

    return name.strip("_")


@cache
def to_camel_case(name: str) -> str:
    """
    Convert name to camelCase.

    Examples:
        >>> to_camel_case("user_name")
        'userName'
        >>> to_camel_case("user-name")
        'userName'
    """
    # First convert to snake case for consistency
    snake = to_snake_case(name)
    parts = snake.split("_")

    if not parts:
        return name

    # First part lowercase, rest title case
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


@cache
def to_pascal_case(name: str) -> str:
    """
    Convert name to PascalCase.

    Examples:
        >>> to_pascal_case("user_name")
        'UserName'
        >>> to_pascal_case("user-name")
        'UserName'
    """
    # First convert to snake case for consistency
    snake = to_snake_case(name)
    parts = snake.split("_")

    # All parts title case
    return "".join(p.capitalize() for p in parts if p)


@cache
def to_kebab_case(name: str) -> str:
    """
    Convert name to kebab-case.

    Examples:
        >>> to_kebab_case("UserName")
        'user-name'
        >>> to_kebab_case("user_name")
        'user-name'
    """
    return to_snake_case(name).replace("_", "-")


@cache
def to_screaming_snake_case(name: str) -> str:
    """
    Convert name to SCREAMING_SNAKE_CASE.

    Examples:
        >>> to_screaming_snake_case("userName")
        'USER_NAME'
    """
    return to_snake_case(name).upper()


# ============================================================================
# Case Converter Registry
# ============================================================================

CASE_CONVERTERS: dict[CaseStyle, callable] = {
    "snake": to_snake_case,
    "camel": to_camel_case,
    "pascal": to_pascal_case,
    "kebab": to_kebab_case,
    "screaming_snake": to_screaming_snake_case,
}


def convert_case(name: str, target_case: CaseStyle) -> str:
    """
    Convert name to target case style.

    Args:
        name: Original name to convert
        target_case: Desired case style

    Returns:
        Converted name

    Raises:
        ValueError: If target_case is not supported
    """
    if target_case not in CASE_CONVERTERS:
        raise ValueError(
            f"Unknown case style: {target_case}. "
            f"Must be one of: {', '.join(CASE_CONVERTERS.keys())}"
        )

    return CASE_CONVERTERS[target_case](name)


# ============================================================================
# Name Sanitization
# ============================================================================


def clean_identifier(name: str) -> str:
    """
    Clean name to be a valid identifier.

    - Removes non-alphanumeric characters (except _ and -)
    - Ensures doesn't start with digit
    - Returns "field" if result is empty

    Args:
        name: Original name

    Returns:
        Cleaned name that can be an identifier
    """
    # Remove non-alphanumeric chars except underscore and hyphen
    cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

    # Remove leading/trailing underscores and hyphens
    cleaned = cleaned.strip("_-")

    # Ensure doesn't start with number
    if cleaned and cleaned[0].isdigit():
        cleaned = f"_{cleaned}"

    # Ensure not empty
    return cleaned or "field"


def resolve_conflict(
    name: str,
    reserved_words: set[str],
    used_names: set[str],
    suffix: str = "_",
) -> str:
    """
    Resolve naming conflicts with reserved words and existing names.

    Args:
        name: Proposed name
        reserved_words: Language reserved words to avoid
        used_names: Already used names to avoid
        suffix: Suffix to add for conflicts (default: "_")

    Returns:
        Name with conflicts resolved
    """
    original = name

    # Check reserved words and builtin types (case-insensitive)
    if name.lower() in {w.lower() for w in reserved_words}:
        name = f"{name}{suffix}"
        logger.debug(f"Reserved word conflict: {original} → {name}")

    # Check for duplicates
    counter = 1
    while name in used_names:
        name = (
            f"{original}{suffix}{counter}" if suffix == "_" else f"{original}{counter}"
        )
        counter += 1
        if counter == 2:  # Log only on first conflict
            logger.debug(f"Duplicate name conflict: {original} → {name}")

    return name


def sanitize_name(
    name: str,
    target_case: CaseStyle,
    reserved_words: set[str] | None = None,
    used_names: set[str] | None = None,
    suffix: str = "_",
) -> str:
    """
    Sanitize and convert a name for safe use in code generation.

    This is the main entry point for name processing. It:
    1. Cleans the name to be a valid identifier
    2. Converts to target case style
    3. Resolves conflicts with reserved words and used names

    Args:
        name: Original name to sanitize
        target_case: Desired case style
        reserved_words: Set of reserved words to avoid
        used_names: Set of already used names to avoid
        suffix: Suffix for conflict resolution

    Returns:
        Sanitized and converted name

    Example:
        >>> sanitize_name("user-name", "pascal", {"class"}, {"User"})
        'UserName'
    """
    reserved_words = reserved_words or set()
    used_names = used_names or set()

    # Step 1: Convert case
    converted = convert_case(name, target_case)

    # Step 2: Clean
    cleaned = clean_identifier(converted)

    # Step 3: Resolve conflicts
    final_name = resolve_conflict(cleaned, reserved_words, used_names, suffix)

    if final_name != name:
        logger.debug(f"Name sanitization: {name} → {final_name}")

    return final_name


# ============================================================================
# Stateful Name Tracker (for tracking names across generation)
# ============================================================================


class NameTracker:
    """
    Tracks used names during code generation.

    This is a simple stateful wrapper around the sanitize_name function
    that maintains a set of used names across multiple calls.
    """

    __slots__ = ("_used_names", "_reserved_words")

    def __init__(self, reserved_words: set[str] | None = None):
        """
        Initialize name tracker.

        Args:
            reserved_words: Set of language reserved words
        """
        self._used_names: set[str] = set()
        self._reserved_words = reserved_words or set()
        logger.debug(
            f"NameTracker initialized with {len(self._reserved_words)} reserved words"
        )

    def sanitize(
        self,
        name: str,
        target_case: CaseStyle,
        suffix: str = "_",
    ) -> str:
        """
        Sanitize name and track it.

        Args:
            name: Original name
            target_case: Desired case style
            suffix: Conflict resolution suffix

        Returns:
            Sanitized name (automatically tracked)
        """
        result = sanitize_name(
            name,
            target_case,
            self._reserved_words,
            self._used_names,
            suffix,
        )
        self._used_names.add(result)
        return result

    def reset(self) -> None:
        """Clear all tracked names."""
        logger.debug(f"Clearing {len(self._used_names)} tracked names")
        self._used_names.clear()

    def add(self, name: str) -> None:
        """Manually add a name to the tracker."""
        self._used_names.add(name)
        logger.debug(f"Manually added name: {name}")

    @property
    def used_names(self) -> frozenset[str]:
        """Get immutable view of used names."""
        return frozenset(self._used_names)
