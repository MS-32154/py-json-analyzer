"""Python options for the interactive code generation interface."""

from typing import Any

from rich.console import Console
from rich.prompt import Confirm

from json_explorer.ui import ask

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

    def get_template_choices(self) -> dict[str, str]:
        return {name: description for name, (description, _) in TEMPLATES.items()}

    def create_template_config(self, template_name: str) -> GeneratorConfig | None:
        if template_name not in TEMPLATES:
            return None
        return GeneratorConfig(language_config=dict(TEMPLATES[template_name][1]))

    def configure_language_specific(self, console: Console) -> dict[str, Any]:
        console.print("\n[bold]Python-Specific Options:[/bold]")
        style = ask(
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
