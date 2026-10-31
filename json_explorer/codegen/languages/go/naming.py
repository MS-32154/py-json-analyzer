"""Go identifier and struct-tag rules.

Generated fields must be exported (start with an uppercase letter) or
encoding/json ignores them. Exported names can never clash with Go keywords
or predeclared identifiers, which are all lowercase, so no reserved-word list
is needed.
"""

import json
import unicodedata

from ...core.naming import to_pascal_case

# Punctuation encoding/json accepts in a tag name (see isValidTag in
# encoding/json/encode.go); letters and digits are always accepted.
_TAG_PUNCTUATION = frozenset("!#$%&()*+-./:;<=>?@[]^_{|}~ ")


def go_identifier(name: str, fallback: str = "Field") -> str:
    """Exported ASCII identifier for a key or type name.

    ``user_id`` -> ``UserId``, ``123abc`` -> ``Field123abc``,
    ``名前`` -> ``Field`` (no ASCII letters to keep; the tag keeps the key).
    """
    ident = "".join(c for c in to_pascal_case(name) if c.isascii())
    if not ident:
        return fallback
    if not ident[0].isalpha():
        ident = fallback + ident
    return ident[0].upper() + ident[1:]


def is_valid_json_tag_name(key: str) -> bool:
    """Whether encoding/json can use ``key`` as a struct-tag name.

    Commas end the name, and quotes and backslashes are rejected. For such
    keys encoding/json silently falls back to the Go field name.
    """
    if not key:
        return False
    for char in key:
        if char in _TAG_PUNCTUATION:
            continue
        category = unicodedata.category(char)
        if not (category.startswith("L") or category == "Nd"):
            return False
    return True


def go_json_tag(key: str, *, omitempty: bool) -> str:
    """Struct tag for a JSON key, as a Go raw string literal."""
    value = key + (",omitempty" if omitempty else "")
    # The tag value is itself a quoted Go string; JSON escaping is compatible.
    return "`json:" + json.dumps(value, ensure_ascii=False) + "`"
