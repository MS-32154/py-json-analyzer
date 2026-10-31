"""Python language plugin."""

from ...core.plugin import CliOption, LanguagePlugin
from .generator import PythonGenerator
from .interactive import PythonInteractiveHandler

PLUGIN = LanguagePlugin(
    name="python",
    display_name="Python",
    generator=PythonGenerator,
    aliases=("py",),
    interactive=PythonInteractiveHandler,
    cli_options=(
        CliOption(
            "--python-style",
            "style",
            "Python code style (default: dataclass)",
            choices=("dataclass", "pydantic", "typeddict"),
        ),
        CliOption(
            "--no-slots",
            "dataclass_slots",
            "Don't use __slots__ in dataclasses",
            value=False,
        ),
        CliOption(
            "--frozen", "dataclass_frozen", "Make dataclasses frozen (immutable)"
        ),
        CliOption(
            "--no-kw-only",
            "dataclass_kw_only",
            "Positional dataclass fields (optional fields are moved last)",
            value=False,
        ),
        CliOption(
            "--pydantic-forbid-extra",
            "pydantic_extra_forbid",
            "Forbid extra fields in Pydantic models",
        ),
    ),
    examples=(
        ("Dataclasses", "--generate python"),
        ("Pydantic models", "--generate python --python-style pydantic"),
        ("TypedDicts", "--generate python --python-style typeddict"),
        ("Frozen dataclasses", "--generate python --frozen"),
    ),
)
