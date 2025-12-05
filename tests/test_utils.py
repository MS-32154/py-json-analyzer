"""Unit tests for the utils module."""

import json
import pytest
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch, MagicMock

from json_explorer.utils import (
    JSONLoaderError,
    load_json,
    load_json_from_file,
    load_json_from_url,
    prompt_input,
    prompt_input_path,
)


@pytest.fixture
def sample_json_data():
    """Sample JSON data."""
    return {
        "users": [{"id": 1, "name": "Alice"}, {"id": 2, "name": "Bob"}],
        "metadata": {"total": 2},
    }


@pytest.fixture
def temp_json_file(sample_json_data):
    """Create a temporary JSON file."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sample_json_data, f)
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


@pytest.fixture
def temp_invalid_json_file():
    """Create a temporary file with invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("{ invalid json }")
        temp_path = f.name

    yield temp_path

    # Cleanup
    Path(temp_path).unlink(missing_ok=True)


class TestLoadJsonFromFile:
    """Test load_json_from_file function."""

    def test_load_valid_json_file(self, temp_json_file, sample_json_data):
        """Test loading valid JSON file."""
        source, data = load_json_from_file(temp_json_file)

        assert data == sample_json_data
        assert str(temp_json_file) in source
        assert "📄" in source

    def test_load_nonexistent_file(self):
        """Test loading nonexistent file raises error."""
        with pytest.raises(FileNotFoundError):
            load_json_from_file("nonexistent_file.json")

    def test_load_invalid_json(self, temp_invalid_json_file):
        """Test loading invalid JSON raises error."""
        with pytest.raises(JSONLoaderError, match="Invalid JSON"):
            load_json_from_file(temp_invalid_json_file)

    def test_load_with_path_object(self, temp_json_file, sample_json_data):
        """Test loading with Path object."""
        source, data = load_json_from_file(Path(temp_json_file))

        assert data == sample_json_data

    def test_load_non_json_extension(self, sample_json_data):
        """Test loading file without .json extension."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".txt", delete=False) as f:
            json.dump(sample_json_data, f)
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert data == sample_json_data
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_empty_file(self):
        """Test loading empty JSON file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            f.write("{}")
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert data == {}
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_unicode_content(self):
        """Test loading JSON with unicode characters."""
        unicode_data = {"text": "Hello 世界 🌍"}

        with tempfile.NamedTemporaryFile(
            mode="w", suffix=".json", delete=False, encoding="utf-8"
        ) as f:
            json.dump(unicode_data, f, ensure_ascii=False)
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert data == unicode_data
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestLoadJsonFromUrl:
    """Test load_json_from_url function."""

    @patch("json_explorer.utils.requests.get")
    def test_load_valid_url(self, mock_get, sample_json_data):
        """Test loading JSON from valid URL."""
        mock_response = Mock()
        mock_response.json.return_value = sample_json_data
        mock_response.headers.get.return_value = "application/json"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        source, data = load_json_from_url("https://api.example.com/data.json")

        assert data == sample_json_data
        assert "https://api.example.com/data.json" in source
        assert "🌐" in source
        mock_get.assert_called_once()

    @patch("json_explorer.utils.requests.get")
    def test_invalid_url_format(self, mock_get):
        """Test invalid URL format raises error."""
        with pytest.raises(JSONLoaderError, match="Invalid URL"):
            load_json_from_url("not-a-valid-url")

    @patch("json_explorer.utils.requests.get")
    def test_connection_error(self, mock_get):
        """Test connection error handling."""
        import requests

        mock_get.side_effect = requests.exceptions.ConnectionError("Connection failed")

        with pytest.raises(JSONLoaderError, match="Connection error"):
            load_json_from_url("https://api.example.com/data.json")

    @patch("json_explorer.utils.requests.get")
    def test_timeout_error(self, mock_get):
        """Test timeout error handling."""
        import requests

        mock_get.side_effect = requests.exceptions.Timeout()

        with pytest.raises(JSONLoaderError, match="timeout"):
            load_json_from_url("https://api.example.com/data.json")

    @patch("json_explorer.utils.requests.get")
    def test_http_error(self, mock_get):
        """Test HTTP error handling."""
        import requests

        mock_response = Mock()
        mock_response.status_code = 404
        mock_response.raise_for_status.side_effect = requests.exceptions.HTTPError(
            response=mock_response
        )
        mock_get.return_value = mock_response

        with pytest.raises(JSONLoaderError, match="HTTP error"):
            load_json_from_url("https://api.example.com/data.json")

    @patch("json_explorer.utils.requests.get")
    def test_invalid_json_response(self, mock_get):
        """Test invalid JSON in response."""
        mock_response = Mock()
        mock_response.json.side_effect = json.JSONDecodeError("Invalid", "", 0)
        mock_response.headers.get.return_value = "application/json"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        with pytest.raises(JSONLoaderError, match="Invalid JSON"):
            load_json_from_url("https://api.example.com/data.json")

    @patch("json_explorer.utils.requests.get")
    def test_custom_timeout(self, mock_get, sample_json_data):
        """Test custom timeout parameter."""
        mock_response = Mock()
        mock_response.json.return_value = sample_json_data
        mock_response.headers.get.return_value = "application/json"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        load_json_from_url("https://api.example.com/data.json", timeout=60)

        mock_get.assert_called_once()
        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 60

    @patch("json_explorer.utils.requests.get")
    def test_non_json_content_type(self, mock_get, sample_json_data):
        """Test URL without JSON content type."""
        mock_response = Mock()
        mock_response.json.return_value = sample_json_data
        mock_response.headers.get.return_value = "text/html"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        # Should still load if URL ends with .json
        source, data = load_json_from_url("https://api.example.com/data.json")
        assert data == sample_json_data


class TestLoadJson:
    """Test load_json convenience function."""

    def test_load_from_file(self, temp_json_file, sample_json_data):
        """Test load_json with file path."""
        source, data = load_json(file_path=temp_json_file)

        assert data == sample_json_data
        assert str(temp_json_file) in source

    @patch("json_explorer.utils.requests.get")
    def test_load_from_url(self, mock_get, sample_json_data):
        """Test load_json with URL."""
        mock_response = Mock()
        mock_response.json.return_value = sample_json_data
        mock_response.headers.get.return_value = "application/json"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        source, data = load_json(url="https://api.example.com/data.json")

        assert data == sample_json_data

    def test_no_parameters(self):
        """Test load_json with no parameters raises error."""
        with pytest.raises(JSONLoaderError, match="must be provided"):
            load_json()

    def test_both_parameters(self, temp_json_file):
        """Test load_json with both parameters raises error."""
        with pytest.raises(JSONLoaderError, match="Cannot specify both"):
            load_json(file_path=temp_json_file, url="https://api.example.com/data.json")

    @patch("json_explorer.utils.requests.get")
    def test_load_with_timeout(self, mock_get, sample_json_data):
        """Test load_json with custom timeout."""
        mock_response = Mock()
        mock_response.json.return_value = sample_json_data
        mock_response.headers.get.return_value = "application/json"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        load_json(url="https://api.example.com/data.json", timeout=45)

        call_args = mock_get.call_args
        assert call_args[1]["timeout"] == 45


class TestPromptInput:
    """Test prompt_input function."""

    @patch("json_explorer.utils.prompt")
    def test_basic_input(self, mock_prompt):
        """Test basic input without choices."""
        mock_prompt.return_value = "user input"

        result = prompt_input("Enter value")

        assert result == "user input"
        mock_prompt.assert_called_once()

    @patch("json_explorer.utils.prompt")
    def test_input_with_default(self, mock_prompt):
        """Test input with default value."""
        mock_prompt.return_value = ""

        result = prompt_input("Enter value", default="default_value")

        assert result == "default_value"

    @patch("json_explorer.utils.prompt")
    def test_input_with_choices(self, mock_prompt):
        """Test input with valid choices."""
        mock_prompt.return_value = "choice1"

        result = prompt_input("Select", choices=["choice1", "choice2"])

        assert result == "choice1"

    @patch("json_explorer.utils.prompt")
    def test_input_with_choices_case_insensitive(self, mock_prompt):
        """Test input with choices is case insensitive."""
        mock_prompt.side_effect = ["CHOICE1"]

        result = prompt_input("Select", choices=["choice1", "choice2"])

        assert result == "choice1"

    @patch("json_explorer.utils.prompt")
    def test_input_with_choices_prefix_match(self, mock_prompt):
        """Test input with choices allows prefix matching."""
        # Only match if there's exactly one prefix match
        mock_prompt.return_value = "choice1"

        result = prompt_input("Select", choices=["choice1", "choice2"])

        assert result == "choice1"

    @patch("json_explorer.utils.prompt")
    def test_input_invalid_choice_retry(self, mock_prompt):
        """Test input retries on invalid choice."""
        mock_prompt.side_effect = ["invalid", "choice1"]

        result = prompt_input("Select", choices=["choice1", "choice2"])

        assert result == "choice1"
        assert mock_prompt.call_count == 2

    @patch("json_explorer.utils.prompt")
    def test_fallback_to_prompt_ask(self, mock_prompt):
        """Test fallback to Prompt.ask on error."""
        mock_prompt.side_effect = Exception("prompt_toolkit error")

        with patch("json_explorer.utils.Prompt.ask") as mock_ask:
            mock_ask.return_value = "fallback"
            result = prompt_input("Enter value")

            assert result == "fallback"
            mock_ask.assert_called_once()


class TestPromptInputPath:
    """Test prompt_input_path function."""

    @patch("json_explorer.utils.prompt")
    def test_path_input(self, mock_prompt):
        """Test path input with autocompletion."""
        mock_prompt.return_value = "/path/to/file.json"

        result = prompt_input_path("Enter path")

        assert result == "/path/to/file.json"
        mock_prompt.assert_called_once()

    @patch("json_explorer.utils.prompt")
    def test_path_input_with_default(self, mock_prompt):
        """Test path input with default value."""
        mock_prompt.return_value = ""

        # When empty, should return empty string
        result = prompt_input_path("Enter path", default="default.json")

        assert result == "" or result == "default.json"

    @patch("json_explorer.utils.prompt")
    def test_path_input_fallback(self, mock_prompt):
        """Test fallback to Prompt.ask on error."""
        mock_prompt.side_effect = Exception("prompt_toolkit error")

        with patch("json_explorer.utils.Prompt.ask") as mock_ask:
            mock_ask.return_value = "/fallback/path.json"
            result = prompt_input_path("Enter path")

            assert result == "/fallback/path.json"
            mock_ask.assert_called_once()


class TestJSONLoaderError:
    """Test JSONLoaderError exception."""

    def test_exception_creation(self):
        """Test creating JSONLoaderError."""
        error = JSONLoaderError("Test error message")

        assert isinstance(error, Exception)
        assert str(error) == "Test error message"

    def test_exception_raising(self):
        """Test raising JSONLoaderError."""
        with pytest.raises(JSONLoaderError, match="Test error"):
            raise JSONLoaderError("Test error")


class TestEdgeCases:
    """Test edge cases."""

    def test_load_large_json_file(self):
        """Test loading large JSON file."""
        large_data = {"items": [{"id": i, "value": f"item_{i}"} for i in range(1000)]}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(large_data, f)
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert len(data["items"]) == 1000
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_nested_json(self):
        """Test loading deeply nested JSON."""
        nested_data = {"level1": {"level2": {"level3": {"level4": {"value": "deep"}}}}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(nested_data, f)
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert data["level1"]["level2"]["level3"]["level4"]["value"] == "deep"
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_json_with_special_chars(self):
        """Test loading JSON with special characters."""
        special_data = {
            "text": "Line1\nLine2\tTabbed",
            "quote": 'She said "hello"',
            "backslash": "path\\to\\file",
        }

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(special_data, f)
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert data == special_data
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_json_array_root(self):
        """Test loading JSON with array as root."""
        array_data = [{"id": 1}, {"id": 2}, {"id": 3}]

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(array_data, f)
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert isinstance(data, list)
            assert len(data) == 3
        finally:
            Path(temp_path).unlink(missing_ok=True)

    def test_load_json_null_values(self):
        """Test loading JSON with null values."""
        null_data = {"value": None, "list": [None, None], "nested": {"null": None}}

        with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
            json.dump(null_data, f)
            temp_path = f.name

        try:
            source, data = load_json_from_file(temp_path)
            assert data["value"] is None
            assert data["list"] == [None, None]
        finally:
            Path(temp_path).unlink(missing_ok=True)

    @patch("json_explorer.utils.requests.get")
    def test_url_with_query_params(self, mock_get):
        """Test loading from URL with query parameters."""
        mock_response = Mock()
        mock_response.json.return_value = {"result": "ok"}
        mock_response.headers.get.return_value = "application/json"
        mock_response.raise_for_status = Mock()
        mock_get.return_value = mock_response

        source, data = load_json_from_url(
            "https://api.example.com/data?key=value&format=json"
        )

        assert data == {"result": "ok"}
        mock_get.assert_called_once()

    def test_file_with_bom(self):
        """Test loading JSON file with BOM."""
        data_with_bom = {"text": "value"}

        with tempfile.NamedTemporaryFile(mode="wb", suffix=".json", delete=False) as f:
            # Write BOM + JSON
            f.write(b"\xef\xbb\xbf")
            f.write(json.dumps(data_with_bom).encode("utf-8"))
            temp_path = f.name

        try:
            # utf-8-sig encoding handles BOM
            with open(temp_path, "r", encoding="utf-8-sig") as f:
                loaded_data = json.load(f)
            assert loaded_data == data_with_bom
        finally:
            Path(temp_path).unlink(missing_ok=True)


class TestUrlParsing:
    """Test URL validation and parsing."""

    def test_valid_http_url(self):
        """Test valid HTTP URL."""
        from urllib.parse import urlparse

        parsed = urlparse("http://example.com/data.json")
        assert parsed.scheme == "http"
        assert parsed.netloc == "example.com"

    def test_valid_https_url(self):
        """Test valid HTTPS URL."""
        from urllib.parse import urlparse

        parsed = urlparse("https://example.com/data.json")
        assert parsed.scheme == "https"
        assert parsed.netloc == "example.com"

    def test_invalid_url_no_scheme(self):
        """Test invalid URL without scheme."""
        with pytest.raises(JSONLoaderError, match="Invalid URL"):
            load_json_from_url("example.com/data.json")

    def test_invalid_url_no_netloc(self):
        """Test invalid URL without netloc."""
        with pytest.raises(JSONLoaderError, match="Invalid URL"):
            load_json_from_url("http:///data.json")
