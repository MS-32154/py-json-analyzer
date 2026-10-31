"""Terminal UI helpers shared by the interactive modes and the CLI:
prompts with completion and history, and small display helpers."""

import os
import sys
from pathlib import Path
from typing import Any

from prompt_toolkit import prompt
from prompt_toolkit.completion import FuzzyCompleter, PathCompleter, WordCompleter
from prompt_toolkit.history import FileHistory, History, InMemoryHistory
from rich import box
from rich.console import Console
from rich.prompt import Prompt
from rich.table import Table

from .logging_config import get_logger

logger = get_logger(__name__)


def user_state_dir() -> Path:
    """Per-user directory for json_explorer state (prompt history).

    - Linux/BSD: ``$XDG_STATE_HOME/json_explorer`` (default ``~/.local/state``)
    - macOS: ``~/Library/Application Support/json_explorer``
    - Windows: ``%LOCALAPPDATA%\\json_explorer``
    """
    if sys.platform == "win32":
        base = Path(os.environ.get("LOCALAPPDATA") or Path.home() / "AppData" / "Local")
    elif sys.platform == "darwin":
        base = Path.home() / "Library" / "Application Support"
    else:
        base = Path(
            os.environ.get("XDG_STATE_HOME") or Path.home() / ".local" / "state"
        )
    return base / "json_explorer"


def _history(name: str) -> History:
    """Prompt history stored in the user state directory, not the current one.

    Falls back to in-memory history if the directory can't be created.
    """
    try:
        state_dir = user_state_dir()
        state_dir.mkdir(parents=True, exist_ok=True)
        return FileHistory(str(state_dir / name))
    except OSError as e:
        logger.debug("Prompt history not persisted: %s", e)
        return InMemoryHistory()


def ask(message: str, default: str | None = None, **kwargs) -> str:
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
        history = _history("input_history")

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


def ask_path(message: str, **kwargs) -> str:
    """
    Input for file paths with autocompletion.
    Falls back to Prompt.ask if prompt_toolkit is unavailable.
    """
    default = kwargs.get("default") or ""
    try:
        history = _history("path_history")
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


def print_metadata(console: Console, metadata: dict[str, Any], title: str) -> None:
    """Show a dict as a two-column table (keys made readable)."""
    table = Table(
        title=title, box=box.SIMPLE, show_header=True, header_style="bold cyan"
    )
    table.add_column("Property", style="bold")
    table.add_column("Value", style="green")
    for key, value in metadata.items():
        table.add_row(key.replace("_", " ").title(), str(value))
    console.print()
    console.print(table)
