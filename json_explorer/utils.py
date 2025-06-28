import json
import requests
from pathlib import Path
from urllib.parse import urlparse


class JSONLoaderError(Exception):
    """Custom exception for JSON loading errors."""

    pass


def load_json_from_file(file_path):
    """
    Load JSON data from a local file.

    Args:
        file_path: Path to the JSON file

    Returns:
        Tuple of (source description, parsed JSON data)

    Raises:
        JSONLoaderError: If file cannot be read or JSON is invalid
        FileNotFoundError: If file doesn't exist
    """
    file_path = Path(file_path)

    if not file_path.exists():
        raise FileNotFoundError(f"File not found: {file_path}")

    if not file_path.suffix.lower() == ".json":
        raise JSONLoaderError(f"File must have .json extension: {file_path}")

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        return f"📁 {file_path}", data
    except json.JSONDecodeError as e:
        raise JSONLoaderError(f"Invalid JSON in file {file_path}: {e}")
    except IOError as e:
        raise JSONLoaderError(f"Error reading file {file_path}: {e}")


def load_json_from_url(url, timeout=30):
    """
    Load JSON data from a URL.

    Args:
        url: URL to fetch JSON from
        timeout: Request timeout in seconds

    Returns:
        Tuple of (source description, parsed JSON data)

    Raises:
        JSONLoaderError: If URL is invalid, request fails, or response isn't valid JSON
    """
    # Validate URL
    parsed_url = urlparse(url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        raise JSONLoaderError(f"Invalid URL: {url}")

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        # Check if response content type is JSON
        content_type = response.headers.get("content-type", "").lower()
        if "application/json" not in content_type and not url.endswith(".json"):
            # Still try to parse, but warn about content type
            pass

        data = response.json()
        return f"🌐 {url}", data

    except requests.exceptions.Timeout:
        raise JSONLoaderError(f"Request timeout for URL: {url}")
    except requests.exceptions.ConnectionError:
        raise JSONLoaderError(f"Connection error for URL: {url}")
    except requests.exceptions.HTTPError as e:
        raise JSONLoaderError(f"HTTP error {e.response.status_code} for URL: {url}")
    except requests.exceptions.RequestException as e:
        raise JSONLoaderError(f"Request error for URL {url}: {e}")
    except json.JSONDecodeError as e:
        raise JSONLoaderError(f"Invalid JSON response from URL {url}: {e}")


def load_json(file_path=None, url=None, timeout=30):
    """
    Load JSON data from either a file or URL.

    Args:
        file_path: Path to local JSON file (mutually exclusive with url)
        url: URL to fetch JSON from (mutually exclusive with file_path)
        timeout: Request timeout in seconds (only used for URLs)

    Returns:
        Tuple of (source description, parsed JSON data)

    Raises:
        JSONLoaderError: If neither or both parameters are provided, or loading fails
        FileNotFoundError: If file doesn't exist
    """
    if not file_path and not url:
        raise JSONLoaderError("Either file_path or url must be provided")

    if file_path and url:
        raise JSONLoaderError("Cannot specify both file_path and url")

    if file_path:
        return load_json_from_file(file_path)
    else:
        return load_json_from_url(url, timeout)
