"""Small terminal output helpers shared by the CLI commands."""

import sys
from typing import Any

from rich import box
from rich.console import Console
from rich.table import Table


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


def write_raw(text: str) -> None:
    """Write text to stdout unchanged, as UTF-8, ending with one newline.

    For output meant to be redirected to a file (generated code, schemas):
    independent of the console code page (e.g. cp1252 on Windows when
    piping), which can't encode every character.
    """
    text = text if text.endswith("\n") else text + "\n"
    if buffer := getattr(sys.stdout, "buffer", None):
        sys.stdout.flush()
        buffer.write(text.encode("utf-8"))
        buffer.flush()
    else:
        sys.stdout.write(text)
        sys.stdout.flush()
