"""Go options for the interactive code generation interface."""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from json_explorer.utils import prompt_input

from ...core.config import GeneratorConfig

# Ready-made configurations offered in the interactive menu.
TEMPLATES: dict[str, tuple[str, dict[str, Any]]] = {
    "default": (
        "Pointers for optional fields, omitempty tags (good for REST APIs)",
        {"package_name": "models"},
    ),
    "no-pointers": (
        "Value types only, no omitempty (zero values instead of nil)",
        {
            "package_name": "models",
            "json_tag_omitempty": False,
            "use_pointers_for_optional": False,
        },
    ),
}


class GoInteractiveHandler:
    """Interactive handler for Go-specific code generation options."""

    __slots__ = ()

    def get_language_info(self) -> dict[str, str]:
        return {
            "description": "Generates Go structs with JSON tags",
            "features": "Exported fields, json tags, pointers for optional fields",
            "use_cases": "REST APIs, configuration, data models, JSON processing",
            "maturity": "Full support",
        }

    def show_configuration_examples(self, console: Console) -> None:
        console.print()
        console.print(
            Panel(
                "[bold]Go options:[/bold]\n"
                "• Pointers for optional fields (tell missing values from zero values)\n"
                "• omitempty on optional fields\n"
                "• Integer type: int, int32 or int64\n"
                "• Float type: float32 or float64\n"
                "• Timestamps: time.Time or string\n\n"
                "[bold]Always:[/bold] exported PascalCase fields, json tags with the\n"
                "original keys, `any` for unknown or mixed values (Go 1.18+)",
                title="⚙️ Go Configuration Options",
                border_style="blue",
            )
        )

    def get_template_choices(self) -> dict[str, str]:
        return {name: description for name, (description, _) in TEMPLATES.items()}

    def create_template_config(self, template_name: str) -> GeneratorConfig | None:
        if template_name not in TEMPLATES:
            return None
        options = dict(TEMPLATES[template_name][1])
        common = {
            k: options.pop(k)
            for k in ("package_name", "json_tag_omitempty")
            if k in options
        }
        return GeneratorConfig(**common, language_config=options)

    def configure_language_specific(self, console: Console) -> dict[str, Any]:
        console.print("\n[bold]Go-Specific Options:[/bold]")
        config: dict[str, Any] = {
            "json_tag_omitempty": Confirm.ask(
                "Add 'omitempty' to optional fields?", default=True
            ),
            "use_pointers_for_optional": Confirm.ask(
                "Use pointers for optional fields?", default=True
            ),
        }
        if Confirm.ask("Configure types?", default=False):
            config["int_type"] = self._input(
                "Integer type",
                choices=["int", "int32", "int64"],
                default="int64",
                console=console,
            )
            config["float_type"] = self._input(
                "Float type",
                choices=["float32", "float64"],
                default="float64",
                console=console,
            )
            config["time_type"] = self._input(
                "Timestamp type",
                choices=["time.Time", "string"],
                default="time.Time",
                console=console,
            )
        return config

    def get_default_config(self) -> dict[str, Any]:
        return {"json_tag_omitempty": True, "use_pointers_for_optional": True}

    def _input(self, message: str, default: str | None = None, **kwargs) -> str:
        return prompt_input(
            message,
            default=default,
            choices=kwargs.get("choices"),
            console=kwargs.get("console"),
        )
