"""Identifier naming for code generation.

Two parts:

- Word splitting and case conversion that understand acronyms
  (``HTTPServer`` -> ``http_server``) and fold accents (``café`` -> ``cafe``).
- A *name plan*: every generated type and field gets its identifier once,
  before rendering, so a declaration and all references to it always agree.
  Each language supplies the function that turns a raw name into a valid
  identifier for it.
"""

import unicodedata
from collections.abc import Callable, Iterable
from dataclasses import dataclass
from functools import cache
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .schema import Field, Schema


def fold_accents(text: str) -> str:
    """Remove combining marks: ``café`` -> ``cafe``, ``naïve`` -> ``naive``."""
    decomposed = unicodedata.normalize("NFKD", text)
    return "".join(c for c in decomposed if not unicodedata.combining(c))


@cache
def split_words(name: str) -> tuple[str, ...]:
    """Split a key into words at separators and case boundaries.

    Acronyms stay together and digits stick to the preceding word::

        userID          -> ('user', 'ID')
        HTTPServer      -> ('HTTP', 'Server')
        XMLHttpRequest  -> ('XML', 'Http', 'Request')
        user2FA         -> ('user2', 'FA')
        first-name      -> ('first', 'name')
    """
    text = fold_accents(name)
    words: list[str] = []
    current = ""
    for i, char in enumerate(text):
        if not char.isalnum():
            if current:
                words.append(current)
                current = ""
            continue
        if current:
            prev = current[-1]
            nxt = text[i + 1] if i + 1 < len(text) else ""
            starts_word = char.isupper() and (
                prev.islower()
                or prev.isdigit()
                or (prev.isupper() and nxt.islower())  # end of an acronym: HTTPServer
            )
            if starts_word:
                words.append(current)
                current = ""
        current += char
    if current:
        words.append(current)
    return tuple(words)


def to_snake_case(name: str) -> str:
    """``userName`` / ``UserName`` / ``user-name`` -> ``user_name``."""
    return "_".join(word.lower() for word in split_words(name))


def to_pascal_case(name: str) -> str:
    """``user_name`` / ``userName`` / ``user-name`` -> ``UserName``."""
    return "".join(word[:1].upper() + word[1:].lower() for word in split_words(name))


# ============================================================================
# Name plan
# ============================================================================


@dataclass(slots=True, frozen=True)
class NamePlan:
    """Final identifiers for every type and field of one generation run."""

    _types: dict[int, str]
    _fields: dict[int, str]

    def type_name(self, schema: Schema) -> str:
        return self._types[id(schema)]

    def field_name(self, field: Field) -> str:
        return self._fields[id(field)]


def unique_name(base: str, used: set[str], separator: str = "") -> str:
    """Return ``base``, or ``base2``, ``base3``... (with ``separator``) if taken."""
    name, n = base, 2
    while name in used:
        name = f"{base}{separator}{n}"
        n += 1
    used.add(name)
    return name


def plan_names(
    schemas: Iterable[Schema],
    *,
    type_identifier: Callable[[str], str],
    field_identifier: Callable[[str], str],
    field_separator: str = "",
) -> NamePlan:
    """Assign unique identifiers to all types (globally) and fields (per type).

    Args:
        schemas: All schemas of the run, in a deterministic order (the first
            one keeps its name when two would collide).
        type_identifier: Turns a schema name into a valid type identifier.
        field_identifier: Turns a JSON key into a valid field identifier.
        field_separator: Put between a field name and its number when two
            keys map to the same identifier (``name_2`` vs ``Name2``).
    """
    schemas = list(schemas)
    used_types: set[str] = set()
    types = {
        id(schema): unique_name(type_identifier(schema.name), used_types)
        for schema in schemas
    }
    fields: dict[int, str] = {}
    for schema in schemas:
        used_fields: set[str] = set()
        for field in schema.fields:
            fields[id(field)] = unique_name(
                field_identifier(field.original_name), used_fields, field_separator
            )
    return NamePlan(types, fields)
