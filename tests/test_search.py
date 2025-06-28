import pytest
from json_explorer.search import JsonSearcher, SearchMode, SearchResult


class TestJsonSearcher:

    @pytest.fixture
    def searcher(self):
        return JsonSearcher()

    @pytest.fixture
    def sample_data(self):
        return {
            "users": [
                {"name": "Alice", "email": "alice@test.com", "age": 30},
                {"name": "Bob", "email": "bob@test.com", "age": 25},
            ],
            "settings": {"theme": "dark", "version": "1.0"},
        }

    def test_search_keys_exact(self, searcher, sample_data):
        results = searcher.search_keys(sample_data, "name")
        assert len(results) == 2
        assert results[0].value == "Alice"
        assert results[1].value == "Bob"

    def test_search_keys_contains(self, searcher, sample_data):
        results = searcher.search_keys(sample_data, "settings", SearchMode.CONTAINS)
        assert len(results) == 1
        assert "settings" in results[0].path

    def test_search_values_exact(self, searcher, sample_data):
        results = searcher.search_values(sample_data, "Alice")
        assert len(results) == 1
        assert results[0].value == "Alice"

    def test_search_values_contains(self, searcher, sample_data):
        results = searcher.search_values(sample_data, "@", SearchMode.CONTAINS)
        assert len(results) == 2  # Both email addresses
        emails = [r.value for r in results]
        assert "alice@test.com" in emails
        assert "bob@test.com" in emails

    def test_search_values_with_type_filter(self, searcher, sample_data):
        results = searcher.search_values(sample_data, 30, value_types={int})
        assert len(results) == 1
        assert results[0].value == 30

    def test_search_key_value_pairs(self, searcher, sample_data):
        results = searcher.search_key_value_pairs(sample_data, "name", "Alice")
        assert len(results) == 1
        assert results[0].value == "Alice"
        assert results[0].parent_key == "name"

    def test_custom_filter_search(self, searcher, sample_data):
        # Find numeric values greater than 25
        results = searcher.search_with_filter(
            sample_data, lambda key, value, depth: isinstance(value, int) and value > 25
        )
        assert len(results) == 1
        assert results[0].value == 30

    def test_max_results_limit(self, searcher, sample_data):
        results = searcher.search_keys(sample_data, "name", max_results=1)
        assert len(results) == 1

    def test_depth_limits(self, searcher, sample_data):
        # Search only at depth 2 and below
        results = searcher.search_values(sample_data, "Alice", max_depth=2)
        assert len(results) == 0  # Alice is at depth 3

        # Search at depth 3 and below
        results = searcher.search_values(sample_data, "Alice", max_depth=3)
        assert len(results) == 1

    def test_no_results(self, searcher, sample_data):
        results = searcher.search_keys(sample_data, "nonexistent")
        assert len(results) == 0

    def test_empty_data(self, searcher):
        results = searcher.search_keys({}, "anything")
        assert len(results) == 0


class TestSearchModes:
    """Test different search modes."""

    @pytest.fixture
    def searcher(self):
        return JsonSearcher()

    def test_exact_match(self, searcher):
        data = {"test": "hello"}
        results = searcher.search_values(data, "hello", SearchMode.EXACT)
        assert len(results) == 1

    def test_contains_match(self, searcher):
        data = {"email": "user@domain.com"}
        results = searcher.search_values(data, "@", SearchMode.CONTAINS)
        assert len(results) == 1

    def test_case_insensitive_match(self, searcher):
        data = {"name": "Alice"}
        results = searcher.search_values(data, "alice", SearchMode.CASE_INSENSITIVE)
        assert len(results) == 1

    def test_startswith_match(self, searcher):
        data = {"prefix": "hello_world"}
        results = searcher.search_values(data, "hello", SearchMode.STARTSWITH)
        assert len(results) == 1

    def test_endswith_match(self, searcher):
        data = {"suffix": "world_test"}
        results = searcher.search_values(data, "test", SearchMode.ENDSWITH)
        assert len(results) == 1

    def test_regex_match(self, searcher):
        data = {"code": "abc123"}
        results = searcher.search_values(data, r"\d+", SearchMode.REGEX)
        assert len(results) == 1


class TestSearchResult:
    """Test SearchResult functionality."""

    def test_basic_result(self):
        result = SearchResult("root.test", "value")
        assert result.path == "root.test"
        assert result.value == "value"
        assert result.data_type == "str"

    def test_result_with_parent(self):
        result = SearchResult("root.key", "value", parent_key="key", depth=1)
        assert result.parent_key == "key"
        assert result.depth == 1

    def test_data_type_detection(self):
        str_result = SearchResult("path", "text")
        assert str_result.data_type == "str"

        int_result = SearchResult("path", 42)
        assert int_result.data_type == "int"

        list_result = SearchResult("path", [1, 2])
        assert list_result.data_type == "list"


class TestComplexData:
    """Test with more complex nested data."""

    @pytest.fixture
    def searcher(self):
        return JsonSearcher()

    @pytest.fixture
    def complex_data(self):
        return {
            "company": {
                "departments": [
                    {
                        "name": "Engineering",
                        "employees": [
                            {"name": "Alice", "skills": ["Python", "JavaScript"]},
                            {"name": "Bob", "skills": ["Java", "Python"]},
                        ],
                    },
                    {
                        "name": "Marketing",
                        "employees": [
                            {"name": "Carol", "skills": ["Design", "Content"]}
                        ],
                    },
                ]
            }
        }

    def test_deep_nested_search(self, searcher, complex_data):
        results = searcher.search_values(complex_data, "Python", SearchMode.CONTAINS)
        assert len(results) == 2  # Found in two skill lists

    def test_nested_key_search(self, searcher, complex_data):
        results = searcher.search_keys(complex_data, "employees")
        assert len(results) == 2  # Two departments have employees

    def test_array_element_search(self, searcher, complex_data):
        results = searcher.search_values(complex_data, "Engineering")
        assert len(results) == 1
        assert "departments[0].name" in results[0].path


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
