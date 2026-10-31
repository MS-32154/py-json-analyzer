"""TypeScript language plugin."""

from ...core.plugin import CliOption, LanguagePlugin
from .generator import TypeScriptGenerator

PLUGIN = LanguagePlugin(
    name="typescript",
    display_name="TypeScript",
    generator=TypeScriptGenerator,
    aliases=("ts",),
    interactive=None,  # not in interactive mode yet
    cli_options=(
        CliOption(
            "--ts-style",
            "style",
            "TypeScript style: interface (default) or zod",
            choices=("interface", "zod"),
        ),
    ),
    examples=(
        ("Interfaces", "--generate typescript"),
        ("Zod schemas with inferred types", "--generate ts --ts-style zod"),
        ("Write to a file", "--generate ts --output models.ts"),
    ),
)
