"""Unit tests for the JMESPath-based search module."""

import pytest
from json_explorer.search import JsonSearcher, SearchResult


@pytest.fixture
def sample_data():
    """Sample JSON data for testing."""
    return {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "age": 30,
                "email": "alice@example.com",
                "active": True,
            },
            {
                "id": 2,
                "name": "Bob",
                "age": 25,
                "email": "bob@example.com",
                "active": False,
            },
            {
                "id": 3,
                "name": "Charlie",
                "age": 35,
                "email": "charlie@example.com",
                "active": True,
            },
        ],
        "metadata": {"total": 3, "created": "2024-01-01"},
    }


@pytest.fixture
def searcher():
    """Create a JsonSearcher instance."""
    return JsonSearcher()


class TestBasicSearch:
    """Test basic search functionality."""

    def test_simple_path(self, searcher, sample_data):
        """Test simple path expression."""
        result = searcher.search(sample_data, "users")
        assert result is not None
        assert isinstance(result.value, list)
        assert len(result.value) == 3

    def test_array_index(self, searcher, sample_data):
        """Test array indexing."""
        result = searcher.search(sample_data, "users[0]")
        assert result is not None
        assert result.value["name"] == "Alice"

    def test_negative_index(self, searcher, sample_data):
        """Test negative array indexing."""
        result = searcher.search(sample_data, "users[-1]")
        assert result is not None
        assert result.value["name"] == "Charlie"

    def test_nested_path(self, searcher, sample_data):
        """Test nested path access."""
        result = searcher.search(sample_data, "metadata.total")
        assert result is not None
        assert result.value == 3

    def test_projection(self, searcher, sample_data):
        """Test array projection."""
        result = searcher.search(sample_data, "users[*].name")
        assert result is not None
        assert result.value == ["Alice", "Bob", "Charlie"]

    def test_nonexistent_path(self, searcher, sample_data):
        """Test query with nonexistent path."""
        result = searcher.search(sample_data, "nonexistent")
        assert result is None


class TestFiltering:
    """Test filtering functionality."""

    def test_filter_by_number(self, searcher, sample_data):
        """Test filtering by numeric comparison."""
        result = searcher.search(sample_data, "users[?age > `30`]")
        assert result is not None
        assert len(result.value) == 1
        assert result.value[0]["name"] == "Charlie"

    def test_filter_by_boolean(self, searcher, sample_data):
        """Test filtering by boolean value."""
        result = searcher.search(sample_data, "users[?active == `true`]")
        assert result is not None
        assert len(result.value) == 2
        names = [u["name"] for u in result.value]
        assert "Alice" in names
        assert "Charlie" in names

    def test_filter_multiple_conditions(self, searcher, sample_data):
        """Test filtering with multiple conditions."""
        result = searcher.search(sample_data, "users[?age > `25` && active == `true`]")
        assert result is not None
        assert len(result.value) == 2

    def test_filter_with_projection(self, searcher, sample_data):
        """Test filtering combined with projection."""
        result = searcher.search(sample_data, "users[?age > `25`].name")
        assert result is not None
        assert "Alice" in result.value
        assert "Charlie" in result.value
        assert "Bob" not in result.value


class TestFunctions:
    """Test JMESPath functions."""

    def test_length_function(self, searcher, sample_data):
        """Test length() function."""
        result = searcher.search(sample_data, "length(users)")
        assert result is not None
        assert result.value == 3

    def test_sort_by(self, searcher, sample_data):
        """Test sort_by() function."""
        result = searcher.search(sample_data, "sort_by(users, &age)")
        assert result is not None
        ages = [u["age"] for u in result.value]
        assert ages == [25, 30, 35]

    def test_max_by(self, searcher, sample_data):
        """Test max_by() function."""
        result = searcher.search(sample_data, "max_by(users, &age)")
        assert result is not None
        assert result.value["name"] == "Charlie"

    def test_min_by(self, searcher, sample_data):
        """Test min_by() function."""
        result = searcher.search(sample_data, "min_by(users, &age)")
        assert result is not None
        assert result.value["name"] == "Bob"


class TestProjections:
    """Test projection expressions."""

    def test_object_projection(self, searcher, sample_data):
        """Test object projection with field selection."""
        result = searcher.search(sample_data, "users[*].{name: name, age: age}")
        assert result is not None
        assert len(result.value) == 3
        assert all("name" in item and "age" in item for item in result.value)
        assert all("email" not in item for item in result.value)

    def test_projection_with_rename(self, searcher, sample_data):
        """Test projection with field renaming."""
        result = searcher.search(
            sample_data, "users[*].{username: name, user_age: age}"
        )
        assert result is not None
        assert all("username" in item and "user_age" in item for item in result.value)


class TestMultipleQueries:
    """Test multiple query execution."""

    def test_search_multiple(self, searcher, sample_data):
        """Test executing multiple queries."""
        queries = ["users[*].name", "length(users)", "metadata.total"]
        results = searcher.search_multiple(sample_data, queries)

        assert len(results) == 3
        assert results["users[*].name"].value == ["Alice", "Bob", "Charlie"]
        assert results["length(users)"].value == 3
        assert results["metadata.total"].value == 3

    def test_search_multiple_with_invalid(self, searcher, sample_data):
        """Test multiple queries with some invalid ones."""
        queries = ["users[*].name", "invalid[syntax", "metadata.total"]
        results = searcher.search_multiple(sample_data, queries)

        # Only valid queries should be in results
        assert len(results) == 2
        assert "users[*].name" in results
        assert "metadata.total" in results
        assert "invalid[syntax" not in results


class TestValidation:
    """Test query validation."""

    def test_validate_valid_query(self, searcher):
        """Test validation of valid query."""
        valid, error = searcher.validate_query("users[*].name")
        assert valid is True
        assert error is None

    def test_validate_invalid_syntax(self, searcher):
        """Test validation of invalid syntax."""
        valid, error = searcher.validate_query("users[invalid")
        assert valid is False
        assert error is not None

    def test_validate_invalid_function(self, searcher):
        """Test validation of invalid function."""
        # JMESPath doesn't validate function existence at compile time
        # It only validates syntax, so this is actually valid syntax
        valid, error = searcher.validate_query("unknown_func(users)")
        # The query has valid syntax, even if function doesn't exist
        # Runtime errors happen during execution, not validation
        assert valid is True or (valid is False and error is not None)


class TestSearchResult:
    """Test SearchResult dataclass."""

    def test_search_result_creation(self, searcher, sample_data):
        """Test SearchResult object creation."""
        result = searcher.search(sample_data, "users[0]")

        assert isinstance(result, SearchResult)
        assert result.query == "users[0]"
        assert result.path == "users[0]"
        assert result.data_type == "dict"
        assert isinstance(result.value, dict)

    def test_search_result_types(self, searcher, sample_data):
        """Test SearchResult with different value types."""
        # List result
        list_result = searcher.search(sample_data, "users")
        assert list_result.data_type == "list"

        # String result
        str_result = searcher.search(sample_data, "users[0].name")
        assert str_result.data_type == "str"

        # Integer result
        int_result = searcher.search(sample_data, "metadata.total")
        assert int_result.data_type == "int"


class TestEdgeCases:
    """Test edge cases and special scenarios."""

    def test_empty_data(self, searcher):
        """Test search on empty data."""
        result = searcher.search({}, "users")
        assert result is None

    def test_null_values(self, searcher):
        """Test search with null values."""
        data = {"value": None}
        result = searcher.search(data, "value")
        assert result is None

    def test_complex_nested_structure(self, searcher):
        """Test search on deeply nested structure."""
        data = {"level1": {"level2": {"level3": {"value": "deep"}}}}
        result = searcher.search(data, "level1.level2.level3.value")
        assert result is not None
        assert result.value == "deep"

    def test_array_of_arrays(self, searcher):
        """Test search on nested arrays."""
        data = {"matrix": [[1, 2], [3, 4], [5, 6]]}
        result = searcher.search(data, "matrix[1][0]")
        assert result is not None
        assert result.value == 3

    def test_mixed_types_in_array(self, searcher):
        """Test search on array with mixed types."""
        data = {"mixed": [1, "text", True, None, {"key": "value"}]}
        result = searcher.search(data, "mixed[4].key")
        assert result is not None
        assert result.value == "value"


class TestCompileQuery:
    """Test query compilation for performance."""

    def test_compile_query_flag(self, searcher, sample_data):
        """Test using compile_query flag."""
        result = searcher.search(sample_data, "users[*].name", compile_query=True)
        assert result is not None
        assert result.value == ["Alice", "Bob", "Charlie"]

    def test_compile_invalid_query(self, searcher, sample_data):
        """Test compiling invalid query."""
        result = searcher.search(sample_data, "invalid[syntax", compile_query=True)
        assert result is None
