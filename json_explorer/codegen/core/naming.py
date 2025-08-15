"""
Naming utilities for safe code generation.

Handles name sanitization, case conversions, keyword conflicts,
and other naming concerns across different programming languages.
"""

import re
from typing import Set, Dict
from enum import Enum


class NamingCase(Enum):
    """Different naming case styles."""

    SNAKE_CASE = "snake"  # user_name
    CAMEL_CASE = "camel"  # userName
    PASCAL_CASE = "pascal"  # UserName
    KEBAB_CASE = "kebab"  # user-name
    SCREAMING_SNAKE = "screaming_snake"  # USER_NAME


class NameSanitizer:
    """Handles name sanitization and case conversion."""

    def __init__(self, reserved_words: Set[str] = None, builtin_types: Set[str] = None):
        """
        Initialize name sanitizer.

        Args:
            reserved_words: Set of language reserved words
            builtin_types: Set of builtin type names that might conflict
        """
        self.reserved_words = reserved_words or set()
        self.builtin_types = builtin_types or set()
        self._name_cache: Dict[str, str] = {}
        self._used_names: Set[str] = set()

    def sanitize_name(
        self,
        name: str,
        target_case: NamingCase = NamingCase.SNAKE_CASE,
        suffix_on_conflict: str = "_",
    ) -> str:
        """
        Sanitize a name for safe use in target language.

        Args:
            name: Original name to sanitize
            target_case: Desired case style
            suffix_on_conflict: Suffix to add for conflicts

        Returns:
            Sanitized name safe for use
        """
        # Use cache if available
        cache_key = f"{name}_{target_case.value}_{suffix_on_conflict}"
        if cache_key in self._name_cache:
            return self._name_cache[cache_key]

        # Step 1: Basic cleanup
        cleaned = self._clean_basic(name)

        # Step 2: Convert to target case
        converted = self._convert_case(cleaned, target_case)

        # Step 3: Handle conflicts
        final_name = self._resolve_conflicts(converted, suffix_on_conflict)

        # Cache and track
        self._name_cache[cache_key] = final_name
        self._used_names.add(final_name)

        return final_name

    def _clean_basic(self, name: str) -> str:
        """Basic name cleanup - remove invalid characters."""
        # Remove non-alphanumeric chars except underscore and hyphen
        cleaned = re.sub(r"[^a-zA-Z0-9_-]", "_", name)

        # Remove leading/trailing underscores and hyphens
        cleaned = cleaned.strip("_-")

        # Ensure doesn't start with number
        if cleaned and cleaned[0].isdigit():
            cleaned = f"_{cleaned}"

        # Ensure not empty
        if not cleaned:
            cleaned = "field"

        return cleaned

    def _convert_case(self, name: str, target_case: NamingCase) -> str:
        """Convert name to target case style."""
        if target_case == NamingCase.SNAKE_CASE:
            return self._to_snake_case(name)
        elif target_case == NamingCase.CAMEL_CASE:
            return self._to_camel_case(name)
        elif target_case == NamingCase.PASCAL_CASE:
            return self._to_pascal_case(name)
        elif target_case == NamingCase.KEBAB_CASE:
            return self._to_kebab_case(name)
        elif target_case == NamingCase.SCREAMING_SNAKE:
            return self._to_snake_case(name).upper()
        else:
            return name

    def _to_snake_case(self, name: str) -> str:
        """Convert to snake_case."""
        # Replace hyphens with underscores
        name = name.replace("-", "_")

        # Insert underscore before uppercase letters
        name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)

        # Convert to lowercase and clean up multiple underscores
        name = name.lower()
        name = re.sub(r"_+", "_", name)

        return name.strip("_")

    def _to_camel_case(self, name: str) -> str:
        """Convert to camelCase."""
        # First convert to snake case, then to camel
        snake = self._to_snake_case(name)
        parts = snake.split("_")

        if not parts:
            return name

        # First part lowercase, rest title case
        return parts[0].lower() + "".join(part.capitalize() for part in parts[1:])

    def _to_pascal_case(self, name: str) -> str:
        """Convert to PascalCase."""
        # First convert to snake case, then to pascal
        snake = self._to_snake_case(name)
        parts = snake.split("_")

        # All parts title case
        return "".join(part.capitalize() for part in parts if part)

    def _to_kebab_case(self, name: str) -> str:
        """Convert to kebab-case."""
        # Convert to snake case, then replace underscores with hyphens
        snake = self._to_snake_case(name)
        return snake.replace("_", "-")

    def _resolve_conflicts(self, name: str, suffix: str) -> str:
        """Resolve naming conflicts with reserved words and existing names."""
        original_name = name

        # Check reserved words and builtin types
        if name.lower() in self.reserved_words or name.lower() in self.builtin_types:
            name = f"{name}{suffix}"

        # Check for duplicates
        counter = 1
        while name in self._used_names:
            if suffix == "_":
                name = f"{original_name}{suffix}{counter}"
            else:
                name = f"{original_name}{counter}"
            counter += 1

        return name

    def reset_used_names(self):
        """Reset the tracking of used names."""
        self._used_names.clear()

    def add_used_name(self, name: str):
        """Manually add a name to the used names set."""
        self._used_names.add(name)
