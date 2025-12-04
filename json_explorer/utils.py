"""Utility functions for loading and processing JSON data.

This module provides functions for loading JSON from files and URLs with
proper error handling and validation.
"""

import json
from pathlib import Path
from typing import Any
from urllib.parse import urlparse

import requests

from rich.console import Console
from rich.prompt import Prompt

from prompt_toolkit import prompt
from prompt_toolkit.history import FileHistory
from prompt_toolkit.completion import PathCompleter, WordCompleter, FuzzyCompleter

from .logging_config import get_logger

logger = get_logger(__name__)


class JSONLoaderError(Exception):
    """Custom exception for JSON loading errors."""

    pass


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
    logger.debug(f"Attempting to load JSON from file: {file_path}")

    if not file_path.exists():
        logger.error(f"File not found: {file_path}")
        raise FileNotFoundError(f"File not found: {file_path}")

    if file_path.suffix.lower() != ".json":
        logger.warning(f"File does not have .json extension: {file_path}")
        # Don't raise, just warn - might still be valid JSON

    try:
        with file_path.open("r", encoding="utf-8") as f:
            data = json.load(f)
        logger.info(f"Successfully loaded JSON from {file_path}")
        return f"📄 {file_path}", data
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON in file {file_path}: {e}", exc_info=True)
        raise JSONLoaderError(f"Invalid JSON in file {file_path}: {e}") from e
    except OSError as e:
        logger.error(f"Error reading file {file_path}: {e}", exc_info=True)
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
    logger.debug(f"Attempting to load JSON from URL: {url}")

    # Validate URL
    parsed_url = urlparse(url)
    if not all([parsed_url.scheme, parsed_url.netloc]):
        logger.error(f"Invalid URL format: {url}")
        raise JSONLoaderError(f"Invalid URL: {url}")

    try:
        response = requests.get(url, timeout=timeout)
        response.raise_for_status()

        # Check content type
        content_type = response.headers.get("content-type", "").lower()
        if "application/json" not in content_type and not url.endswith(".json"):
            logger.warning(f"URL {url} does not have JSON content type: {content_type}")

        data = response.json()
        logger.info(f"Successfully loaded JSON from {url}")
        return f"🌐 {url}", data

    except requests.exceptions.Timeout:
        logger.error(f"Request timeout for URL: {url}")
        raise JSONLoaderError(f"Request timeout for URL: {url}")
    except requests.exceptions.ConnectionError as e:
        logger.error(f"Connection error for URL {url}: {e}")
        raise JSONLoaderError(f"Connection error for URL: {url}") from e
    except requests.exceptions.HTTPError as e:
        logger.error(f"HTTP error {e.response.status_code} for URL: {url}")
        raise JSONLoaderError(
            f"HTTP error {e.response.status_code} for URL: {url}"
        ) from e
    except requests.exceptions.RequestException as e:
        logger.error(f"Request error for URL {url}: {e}", exc_info=True)
        raise JSONLoaderError(f"Request error for URL {url}: {e}") from e
    except json.JSONDecodeError as e:
        logger.error(f"Invalid JSON response from URL {url}: {e}", exc_info=True)
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
        logger.error("Neither file_path nor url provided")
        raise JSONLoaderError("Either file_path or url must be provided")

    if file_path and url:
        logger.error("Both file_path and url provided")
        raise JSONLoaderError("Cannot specify both file_path and url")

    if file_path:
        return load_json_from_file(file_path)
    else:
        return load_json_from_url(url, timeout)


def prompt_input(message: str, default: str | None = None, **kwargs) -> str:
    """
    User friendly input with optional choices and autocompletion.
    Falls back to Prompt.ask if prompt_toolkit is unavailable.

    Args:
        message: Prompt message.
        default: Default value if user enters nothing.
        kwargs: May include:
                    - 'choices' (list of strings) for tab completion,
                    - `console` (rich console object) for rich Console instance to print messages.

    Returns:
        User input as string (or default if empty).
    """
    choices = kwargs.get("choices")
    console = kwargs.get("console") or Console()
    try:

        history = FileHistory(".json_explorer_input_history")

        if choices:
            str_choices = [str(c) for c in choices]
            completer = FuzzyCompleter(WordCompleter(str_choices, ignore_case=True))
            display_message = f"{message} ({'/'.join(str_choices)})"

            while True:
                text = prompt(
                    f"{display_message} > ",
                    default=default or "",
                    history=history,
                    completer=completer,
                    complete_while_typing=True,
                ).strip()

                if not text and default is not None:
                    return default

                if text in str_choices:
                    return text
                lowered = text.lower()
                ci_matches = [c for c in str_choices if c.lower() == lowered]
                if ci_matches:
                    return ci_matches[0]

                prefix_matches = [
                    c for c in str_choices if c.lower().startswith(lowered)
                ]
                if len(prefix_matches) == 1:
                    return prefix_matches[0]

                console.print(f"[red]Invalid choice: {text}[/red]")

        # Free text input
        return prompt(
            f"{message} > ", default=default or "", history=history
        ).strip() or (default or "")

    except Exception:
        return Prompt.ask(message, default=default, **kwargs)


def prompt_input_path(message: str, **kwargs) -> str:
    """
    Input for file paths with autocompletion.
    Falls back to Prompt.ask if prompt_toolkit is unavailable.
    """
    default = kwargs.get("default") or ""
    try:

        history = FileHistory(".json_explorer_path_history")
        completer = PathCompleter(expanduser=True)

        return prompt(
            f"{message} > ",
            default=default,
            history=history,
            completer=completer,
            complete_while_typing=True,
        ).strip()

    except Exception:
        return Prompt.ask(message)
