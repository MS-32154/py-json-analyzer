"""Utility functions for loading and processing JSON data.

This module provides functions for loading JSON from files and URLs with
proper error handling and validation.
"""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from json_explorer.errors import JsonExplorerError

from .logging_config import get_logger

logger = get_logger(__name__)


class JSONLoaderError(JsonExplorerError):
    """Custom exception for JSON loading errors."""


def load_json_from_file(file_path: str | Path) -> tuple[str, Any]:
    """Load JSON data from a local file.

    Args:
        file_path: Path to the JSON file.

    Returns:
        Tuple of (source description, parsed JSON data).

    Raises:
        FileNotFoundError: If file doesn't exist.
        JSONLoaderError: If file cannot be read or JSON is invalid.
    """
    file_path = Path(file_path)
    logger.debug("Attempting to load JSON from file: %s", file_path)

    if not file_path.exists():
        logger.debug("File not found: %s", file_path)
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() != ".json":
        logger.warning("File does not have .json extension: %s", file_path)
        # Don't raise, just warn - might still be valid JSON

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info("Successfully loaded JSON from %s", file_path)
        return f"📄 {file_path}", data
    except json.JSONDecodeError as e:
        logger.debug("Invalid JSON in file %s: %s", file_path, e, exc_info=True)
        raise JSONLoaderError(f"Invalid JSON in file {file_path}: {e}") from e
    except OSError as e:
        logger.debug("Error reading file %s: %s", file_path, e, exc_info=True)
        raise JSONLoaderError(f"Error reading file {file_path}: {e}") from e


def load_json_from_url(url: str, timeout: int = 30) -> tuple[str, Any]:
    """Load JSON data from a URL.

    Args:
        url: URL to fetch JSON from.
        timeout: Request timeout in seconds.

    Returns:
        Tuple of (source description, parsed JSON data).

    Raises:
        JSONLoaderError: If URL is invalid, request fails, or response isn't valid JSON.
    """
    logger.debug("Attempting to load JSON from URL: %s", url)

    # Validate URL
    parsed_url = urlparse(url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        logger.debug("Invalid URL format: %s", url)
        raise JSONLoaderError(f"Invalid URL: {url}")

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get("content-type", "").lower()
        if "application/json" not in content_type and not url.endswith(".json"):
            logger.warning(
                "URL %s does not have JSON content type: %s", url, content_type
            )

        data = response.json()
        logger.info("Successfully loaded JSON from %s", url)
        return f"🌐 {url}", data

    except requests.exceptions.Timeout as e:
        logger.debug("Request timeout for URL: %s", url)
        raise JSONLoaderError(f"Request timeout for URL: {url}") from e
    except requests.exceptions.ConnectionError as e:
        logger.debug("Connection error for URL %s: %s", url, e)
        raise JSONLoaderError(f"Connection error for URL: {url}") from e
    except requests.exceptions.HTTPError as e:
        logger.debug("HTTP error %s for URL: %s", e.response.status_code, url)
        raise JSONLoaderError(
            f"HTTP error {e.response.status_code} for URL: {url}"
        ) from e
    except requests.exceptions.RequestException as e:
        logger.debug("Request error for URL %s: %s", url, e, exc_info=True)
        raise JSONLoaderError(f"Request error for URL {url}: {e}") from e
    except json.JSONDecodeError as e:
        logger.debug("Invalid JSON response from URL %s: %s", url, e, exc_info=True)
        raise JSONLoaderError(f"Invalid JSON response from URL {url}: {e}") from e


def load_json(
    file_path: str | Path | None = None,
    url: str | None = None,
    timeout: int = 30,
) -> tuple[str, Any]:
    """Load JSON data from either a file or URL.

    Args:
        file_path: Path to local JSON file (mutually exclusive with url).
        url: URL to fetch JSON from (mutually exclusive with file_path).
        timeout: Request timeout in seconds (only used for URLs).

    Returns:
        Tuple of (source description, parsed JSON data).

    Raises:
        JSONLoaderError: If neither or both parameters are provided, or loading fails.
        FileNotFoundError: If file doesn't exist.
    """
    if not file_path and not url:
        logger.debug("Neither file_path nor url provided")
        raise JSONLoaderError("Either file_path or url must be provided")

    if file_path and url:
        logger.debug("Both file_path and url provided")
        raise JSONLoaderError("Cannot specify both file_path and url")

    if file_path:
        return load_json_from_file(file_path)
    assert url is not None  # one of them is set (checked above)
    return load_json_from_url(url, timeout)
