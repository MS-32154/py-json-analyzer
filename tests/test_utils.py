import pytest
import json
import tempfile
from pathlib import Path
from json_explorer.utils import (
    load_json_from_file,
    load_json_from_url,
    load_json,
    JSONLoaderError,
)

import requests
from unittest.mock import patch, Mock


def test_load_json_from_valid_file():
    data = {"key": "value"}
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name

    source, loaded = load_json_from_file(tmp_path)
    assert source.startswith("📁")
    assert loaded == data

    Path(tmp_path).unlink()


def test_load_json_from_invalid_file_extension():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".txt", delete=False) as tmp:
        tmp.write('{"key": "value"}')
        tmp_path = tmp.name

    with pytest.raises(JSONLoaderError, match="File must have .json extension"):
        load_json_from_file(tmp_path)

    Path(tmp_path).unlink()


def test_load_json_from_invalid_json():
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        tmp.write("{invalid json}")
        tmp_path = tmp.name

    with pytest.raises(JSONLoaderError, match="Invalid JSON"):
        load_json_from_file(tmp_path)

    Path(tmp_path).unlink()


@patch("json_explorer.utils.requests.get")
def test_load_json_from_valid_url(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"url": "data"}
    mock_get.return_value = mock_response

    source, data = load_json_from_url("http://example.com/data.json")
    assert source.startswith("🌐")
    assert data == {"url": "data"}


@patch("json_explorer.utils.requests.get")
def test_load_json_from_invalid_url(mock_get):
    with pytest.raises(JSONLoaderError, match="Invalid URL"):
        load_json_from_url("invalid-url")


@patch("json_explorer.utils.requests.get", side_effect=requests.exceptions.Timeout)
def test_load_json_url_timeout(mock_get):
    with pytest.raises(JSONLoaderError, match="Request timeout"):
        load_json_from_url("http://example.com/data.json")


def test_load_json_file_only():
    data = {"hello": "world"}
    with tempfile.NamedTemporaryFile(mode="w+", suffix=".json", delete=False) as tmp:
        json.dump(data, tmp)
        tmp_path = tmp.name

    source, result = load_json(file_path=tmp_path)
    assert result == data

    Path(tmp_path).unlink()


@patch("json_explorer.utils.requests.get")
def test_load_json_url_only(mock_get):
    mock_response = Mock()
    mock_response.raise_for_status.return_value = None
    mock_response.headers = {"content-type": "application/json"}
    mock_response.json.return_value = {"hello": "internet"}
    mock_get.return_value = mock_response

    source, data = load_json(url="http://test.com")
    assert data == {"hello": "internet"}


def test_load_json_missing_args():
    with pytest.raises(
        JSONLoaderError, match="Either file_path or url must be provided"
    ):
        load_json()


def test_load_json_both_args():
    with pytest.raises(JSONLoaderError, match="Cannot specify both"):
        load_json(file_path="file.json", url="http://test.com")
