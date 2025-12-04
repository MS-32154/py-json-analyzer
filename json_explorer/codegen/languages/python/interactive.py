"""
Python-specific interactive handler.

Provides Python-specific configuration options, templates, and examples
for the interactive code generation interface.
"""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from json_explorer.utils import prompt_input
from ...core.config import GeneratorConfig
from .config import (
    get_dataclass_config,
    get_pydantic_config,
    get_typeddict_config,
    get_strict_dataclass_config,
)

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Python Interactive Handler
# ============================================================================


class PythonInteractiveHandler:
    """Interactive handler for Python-specific code generation options."""

    __slots__ = ()

    def get_language_info(self) -> dict[str, str]:
        """Get Python-specific information for display."""
        return {
            "description": "Generates Python dataclasses, Pydantic models, or TypedDict",
            "features": "Multiple styles, type hints, optional fields, modern Python 3.10+",
            "use_cases": "REST APIs, data validation, type checking, configuration",
            "maturity": "Full support with multiple styles and templates",
        }

    def show_configuration_examples(self, console: Console) -> None:
        """Show Python-specific configuration examples."""
        config_panel = Panel(
            """[bold]Python Configuration Examples:[/bold]

[green]Dataclass Style:[/green]
• Standard Python dataclasses
• Optional slots and frozen support
• Python 3.10+ features (kw_only)
• Type hints with | for unions

[green]Pydantic Style:[/green]
• Pydantic v2 BaseModel
• Runtime validation
• Field aliases for JSON keys
• ConfigDict for model configuration

[green]TypedDict Style:[/green]
• Pure type hints (no runtime)
• NotRequired for optional fields
• Lightweight type checking
• Compatible with mypy/pyright

[bold]Key Python Features:[/bold]
• Modern type hints (list[T], T | None)
• Optional field handling
• Preserved JSON field names
• Docstrings for descriptions
• Import optimization
• Snake_case field names
• PascalCase class names""",
            title="⚙️ Python Configuration Options",
            border_style="blue",
        )

        console.print()
        console.print(config_panel)

    def get_template_choices(self) -> dict[str, str]:
        """Get available Python configuration templates."""
        return {
            "dataclass": "Standard Python dataclasses with type hints",
            "pydantic": "Pydantic v2 models with validation and Field configuration",
            "typeddict": "TypedDict classes for pure type hints",
            "strict-dataclass": "Frozen, slotted dataclasses for immutable data",
        }

    def create_template_config(
        self,
        template_name: str,
    ) -> GeneratorConfig | None:
        """Create configuration from Python template."""
        match template_name:
            case "dataclass":
                return GeneratorConfig(
                    package_name="models",
                    add_comments=True,
                    language_config=get_dataclass_config().to_dict(),
                )

            case "pydantic":
                return GeneratorConfig(
                    package_name="models",
                    add_comments=True,
                    language_config=get_pydantic_config().to_dict(),
                )

            case "typeddict":
                return GeneratorConfig(
                    package_name="types",
                    add_comments=True,
                    language_config=get_typeddict_config().to_dict(),
                )

            case "strict-dataclass":
                return GeneratorConfig(
                    package_name="models",
                    add_comments=True,
                    language_config=get_strict_dataclass_config().to_dict(),
                )

            case _:
                return None

    def configure_language_specific(
        self,
        console: Console,
    ) -> dict[str, Any]:
        """Handle Python-specific configuration options."""
        python_config = {}

        console.print("\n[bold]Python-Specific Options:[/bold]")

        # Style selection
        style = self._input(
            "Select Python style",
            choices=["dataclass", "pydantic", "typeddict"],
            default="dataclass",
        )
        python_config["style"] = style

        # Optional field handling
        python_config["use_optional"] = Confirm.ask(
            "Use type unions (T | None) for optional fields?",
            default=True,
        )

        # Style-specific configuration
        match style:
            case "dataclass":
                python_config.update(self._configure_dataclass(console))
            case "pydantic":
                python_config.update(self._configure_pydantic(console))
            case "typeddict":
                python_config.update(self._configure_typeddict(console))

        logger.info(f"Python-specific config collected: style={style}")
        return python_config

    def _configure_dataclass(self, console: Console) -> dict[str, Any]:
        """Configure dataclass-specific options."""
        config = {}

        console.print("\n[cyan]Dataclass Options:[/cyan]")

        config["dataclass_slots"] = Confirm.ask(
            "Use __slots__ for memory optimization?",
            default=True,
        )

        config["dataclass_frozen"] = Confirm.ask(
            "Make dataclasses immutable (frozen)?",
            default=False,
        )

        config["dataclass_kw_only"] = Confirm.ask(
            "Require keyword-only arguments?",
            default=False,
        )

        return config

    def _configure_pydantic(self, console: Console) -> dict[str, Any]:
        """Configure Pydantic-specific options."""
        config = {}

        console.print("\n[cyan]Pydantic Options:[/cyan]")

        config["pydantic_use_field"] = Confirm.ask(
            "Use Field() for metadata?",
            default=True,
        )

        if config["pydantic_use_field"]:
            config["pydantic_use_alias"] = Confirm.ask(
                "Generate field aliases for JSON keys?",
                default=True,
            )

        config["pydantic_config_dict"] = Confirm.ask(
            "Generate model_config?",
            default=True,
        )

        if config["pydantic_config_dict"]:
            config["pydantic_extra_forbid"] = Confirm.ask(
                "Forbid extra fields (strict mode)?",
                default=False,
            )

        return config

    def _configure_typeddict(self, console: Console) -> dict[str, Any]:
        """Configure TypedDict-specific options."""
        config = {}

        console.print("\n[cyan]TypedDict Options:[/cyan]")

        config["typeddict_total"] = Confirm.ask(
            "Make all fields required by default (total=True)?",
            default=False,
        )

        return config

    def get_default_config(self) -> dict[str, Any]:
        """Get default Python configuration for quick setup."""
        return {
            "style": "dataclass",
            "use_optional": True,
            "dataclass_slots": True,
            "dataclass_frozen": False,
            "dataclass_kw_only": False,
        }

    def show_examples(self, console: Console) -> None:
        """Show Python code generation examples."""
        examples_panel = Panel(
            """[bold]📝 Python Generation Examples:[/bold]

[bold]Input JSON:[/bold]
```json
{
  "user_id": 123,
  "name": "John",
  "email": null,
  "tags": ["python", "coding"]
}
```

[bold]Dataclass Output:[/bold]
```python
@dataclass(slots=True)
class Root:
    user_id: int
    name: str
    email: str | None = None
    tags: list[str]
```

[bold]Pydantic Output:[/bold]
```python
class Root(BaseModel):
    model_config = ConfigDict(
        extra="ignore",
        populate_by_name=True,
    )
    
    user_id: int = Field(alias="user_id")
    name: str
    email: str | None = Field(default=None)
    tags: list[str]
```

[bold]TypedDict Output:[/bold]
```python
class Root(TypedDict, total=False):
    user_id: int
    name: str
    email: NotRequired[str | None]
    tags: list[str]
```""",
            title="🎯 Code Examples",
            border_style="green",
        )

        console.print()
        console.print(examples_panel)

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """
        Validate Python-specific configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of warning messages (empty if valid)
        """
        warnings = []
        style = config.get("style", "dataclass")

        # Style-specific validations
        match style:
            case "dataclass":
                if config.get("dataclass_frozen") and not config.get("dataclass_slots"):
                    warnings.append(
                        "Consider enabling slots with frozen for better performance"
                    )

            case "pydantic":
                if not config.get("pydantic_use_field"):
                    warnings.append(
                        "Disabling Field() means no aliases or validation metadata"
                    )

                if config.get("pydantic_extra_forbid"):
                    warnings.append(
                        "extra='forbid' will reject any fields not in the model"
                    )

            case "typeddict":
                warnings.append(
                    "TypedDict provides no runtime validation - "
                    "consider Pydantic for validation"
                )

                if not config.get("use_optional"):
                    warnings.append(
                        "TypedDict without NotRequired may cause type checking issues"
                    )

        if warnings:
            logger.info(f"Config validation: {len(warnings)} warnings")

        return warnings

    # ========================================================================
    # prompt_toolkit integration
    # ========================================================================

    def _input(self, message: str, default: str | None = None, **kwargs) -> str:
        console = kwargs.get("console") or None
        return prompt_input(
            message, default=default, choices=kwargs.get("choices"), console=console
        )
