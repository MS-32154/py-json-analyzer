"""
Tests for core naming utilities.
"""

from json_explorer.codegen.core.naming import (
    to_snake_case,
    to_camel_case,
    to_pascal_case,
    sanitize_name,
    NameTracker,
)


class TestCaseConversion:
    """Test case conversion functions."""

    def test_to_snake_case(self):
        assert to_snake_case("UserName") == "user_name"
        assert to_snake_case("user-name") == "user_name"
        assert to_snake_case("userName") == "user_name"

    def test_to_camel_case(self):
        assert to_camel_case("user_name") == "userName"
        assert to_camel_case("UserName") == "userName"
        assert to_camel_case("user-name") == "userName"

    def test_to_pascal_case(self):
        assert to_pascal_case("user_name") == "UserName"
        assert to_pascal_case("userName") == "UserName"
        assert to_pascal_case("user-name") == "UserName"


class TestSanitizeName:
    """Test name sanitization."""

    def test_basic_sanitization(self):
        result = sanitize_name("user-name", "snake")
        assert result == "user_name"

    def test_reserved_word_conflict(self):
        reserved = {"class", "def"}
        result = sanitize_name("class", "snake", reserved_words=reserved)
        assert result == "class_"

    def test_duplicate_name_conflict(self):
        used = {"user"}
        result = sanitize_name("user", "snake", used_names=used)
        assert result == "user_1"

    def test_invalid_characters(self):
        result = sanitize_name("user@name!", "snake")
        assert result == "user_name"

    def test_starts_with_digit(self):
        result = sanitize_name("123user", "snake")
        assert result == "_123user"


class TestNameTracker:
    """Test NameTracker stateful sanitization."""

    def test_tracks_used_names(self):
        tracker = NameTracker()
        name1 = tracker.sanitize("user", "snake")
        name2 = tracker.sanitize("user", "snake")

        assert name1 == "user"
        assert name2 == "user_1"

    def test_reserved_words(self):
        tracker = NameTracker(reserved_words={"class"})
        result = tracker.sanitize("class", "pascal")
        assert result == "Class_"

    def test_reset(self):
        tracker = NameTracker()
        tracker.sanitize("user", "snake")
        tracker.reset()

        result = tracker.sanitize("user", "snake")
        assert result == "user"
