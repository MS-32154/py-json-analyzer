"""Language plugins: everything the tool knows about one target language.

A plugin bundles the generator class, aliases, the
language's CLI flags and its usage examples. The registry loads the built-in
plugins and any installed through the ``json_explorer.languages`` entry-point
group, so adding a language means adding one package.
"""

import argparse
from dataclasses import dataclass
from typing import Any

from .generator import CodeGenerator


@dataclass(frozen=True, slots=True)
class CliOption:
    """A command-line flag that sets one configuration option.

    Without ``choices`` the flag is a switch that sets ``option`` to
    ``value``; with ``choices`` it takes one of them as its argument.
    """

    flag: str
    option: str
    help: str
    value: Any = True
    choices: tuple[str, ...] | None = None

    @property
    def dest(self) -> str:
        return self.flag.lstrip("-").replace("-", "_")


@dataclass(frozen=True, slots=True)
class LanguagePlugin:
    """One target language."""

    name: str
    generator: type[CodeGenerator]
    aliases: tuple[str, ...] = ()
    cli_options: tuple[CliOption, ...] = ()
    examples: tuple[tuple[str, str], ...] = ()  # (description, CLI arguments)
    display_name: str = ""

    @property
    def title(self) -> str:
        return self.display_name or self.name.title()

    def add_cli_arguments(self, parser: argparse.ArgumentParser) -> None:
        if not self.cli_options:
            return
        group = parser.add_argument_group(f"{self.title}-specific options")
        for opt in self.cli_options:
            if opt.choices:
                group.add_argument(
                    opt.flag, dest=opt.dest, choices=opt.choices, help=opt.help
                )
            else:
                group.add_argument(
                    opt.flag, dest=opt.dest, action="store_true", help=opt.help
                )

    def config_from_args(self, args: argparse.Namespace) -> dict[str, Any]:
        """Configuration options set by this language's flags."""
        config: dict[str, Any] = {}
        for opt in self.cli_options:
            given = getattr(args, opt.dest, None)
            if given:
                config[opt.option] = given if opt.choices else opt.value
        return config
