"""Python options for the interactive code generation interface."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from json_explorer.utils import prompt_input

from ...core.config import GeneratorConfig

# Ready-made configurations offered in the interactive menu.
TEMPLATES: dict[str, tuple[str, dict[str, Any]]] = {
    "dataclass": ("Standard dataclasses with type hints", {"style": "dataclass"}),
    "frozen-dataclass": (
        "Immutable, keyword-only dataclasses",
        {"style": "dataclass", "dataclass_frozen": True, "dataclass_kw_only": True},
    ),
    "pydantic": (
        "Pydantic v2 models: validation and aliases for JSON keys",
        {"style": "pydantic"},
    ),
    "typeddict": (
        "TypedDict: type hints for the dicts json.load returns",
        {"style": "typeddict"},
    ),
}


class PythonInteractiveHandler:
    """Interactive handler for Python-specific code generation options."""

    __slots__ = ()

    def get_language_info(self) -> dict[str, str]:
        return {
            "description": "Generates Python dataclasses, Pydantic models, or TypedDict",
            "features": "Three styles, modern type hints (list[T], T | None)",
            "use_cases": "REST APIs, data validation, type checking, configuration",
            "maturity": "Full support",
        }

    def show_configuration_examples(self, console: Console) -> None:
        console.print()
        console.print(
            Panel(
                "[green]Dataclass:[/green] slots, frozen and keyword-only options\n"
                "[green]Pydantic:[/green] runtime validation; aliases map fields to JSON keys;\n"
                "  extra keys ignored or forbidden\n"
                "[green]TypedDict:[/green] describes the dict as-is (original keys;\n"
                "  NotRequired for optional keys)\n\n"
                "[bold]Always:[/bold] PascalCase classes, snake_case fields (dataclass,\n"
                "Pydantic), T | None for optional values",
                title="⚙️ Python Configuration Options",
                border_style="blue",
            )
        )

    def get_template_choices(self) -> dict[str, str]:
        return {name: description for name, (description, _) in TEMPLATES.items()}

    def create_template_config(self, template_name: str) -> GeneratorConfig | None:
        if template_name not in TEMPLATES:
            return None
        return GeneratorConfig(language_config=dict(TEMPLATES[template_name][1]))

    def configure_language_specific(self, console: Console) -> dict[str, Any]:
        console.print("\n[bold]Python-Specific Options:[/bold]")
        style = self._input(
            "Select Python style",
            choices=["dataclass", "pydantic", "typeddict"],
            default="dataclass",
            console=console,
        )
        config: dict[str, Any] = {"style": style}
        match style:
            case "dataclass":
                config["dataclass_slots"] = Confirm.ask("Use __slots__?", default=True)
                config["dataclass_frozen"] = Confirm.ask(
                    "Make dataclasses immutable (frozen)?", default=False
                )
                config["dataclass_kw_only"] = Confirm.ask(
                    "Keyword-only arguments?", default=True
                )
            case "pydantic":
                config["pydantic_config_dict"] = Confirm.ask(
                    "Generate model_config?", default=True
                )
                if config["pydantic_config_dict"]:
                    config["pydantic_extra_forbid"] = Confirm.ask(
                        "Forbid extra fields (strict mode)?", default=False
                    )
        return config

    def get_default_config(self) -> dict[str, Any]:
        return {"style": "dataclass"}

    def _input(self, message: str, default: str | None = None, **kwargs) -> str:
        return prompt_input(
            message,
            default=default,
            choices=kwargs.get("choices"),
            console=kwargs.get("console"),
        )
