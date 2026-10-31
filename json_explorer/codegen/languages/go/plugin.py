"""Go language plugin."""

from ...core.plugin import CliOption, LanguagePlugin
from .generator import GoGenerator
from .interactive import GoInteractiveHandler

PLUGIN = LanguagePlugin(
    name="go",
    display_name="Go",
    generator=GoGenerator,
    aliases=("golang",),
    interactive=GoInteractiveHandler,
    cli_options=(
        CliOption(
            "--no-pointers",
            "use_pointers_for_optional",
            "Don't use pointers for optional fields in Go",
            value=False,
        ),
        CliOption(
            "--no-omitempty",
            "json_tag_omitempty",
            "Don't add omitempty to JSON tags in Go",
            value=False,
        ),
    ),
    examples=(
        ("Generate structs", "--generate go"),
        ("Write to a file", "--generate go --output models.go"),
        ("Custom package name", "--generate go --package-name models"),
        ("Value types only (no pointers)", "--generate go --no-pointers"),
    ),
)
