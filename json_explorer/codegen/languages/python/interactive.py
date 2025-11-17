"""
Python-specific interactive handler for code generation.

Provides Python-specific configuration options, templates, and information.
"""

from typing import Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ...core.config import GeneratorConfig
from .config import (
    get_dataclass_config,
    get_pydantic_config,
    get_typeddict_config,
    get_strict_dataclass_config,
    PythonStyle,
)


class PythonInteractiveHandler:
    """Interactive handler for Python-specific code generation options."""

    def get_language_info(self) -> Dict[str, str]:
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

    def get_template_choices(self) -> Dict[str, str]:
        """Get available Python configuration templates."""
        return {
            "dataclass": "Standard Python dataclasses with type hints",
            "pydantic": "Pydantic v2 models with validation and Field configuration",
            "typeddict": "TypedDict classes for pure type hints",
            "strict-dataclass": "Frozen, slotted dataclasses for immutable data",
        }

    def create_template_config(self, template_name: str) -> Optional[GeneratorConfig]:
        """Create configuration from Python template."""
        if template_name == "dataclass":
            python_config = get_dataclass_config()
            return GeneratorConfig(
                package_name="models",
                add_comments=True,
                language_config=python_config.__dict__,
            )

        elif template_name == "pydantic":
            python_config = get_pydantic_config()
            return GeneratorConfig(
                package_name="models",
                add_comments=True,
                language_config=python_config.__dict__,
            )

        elif template_name == "typeddict":
            python_config = get_typeddict_config()
            return GeneratorConfig(
                package_name="types",
                add_comments=True,
                language_config=python_config.__dict__,
            )

        elif template_name == "strict-dataclass":
            python_config = get_strict_dataclass_config()
            return GeneratorConfig(
                package_name="models",
                add_comments=True,
                language_config=python_config.__dict__,
            )

        return None

    def configure_language_specific(self, console: Console) -> Dict[str, Any]:
        """Handle Python-specific configuration options."""
        python_config = {}

        console.print("\n[bold]Python-Specific Options:[/bold]")

        # Style selection
        style = Prompt.ask(
            "Select Python style",
            choices=["dataclass", "pydantic", "typeddict"],
            default="dataclass",
        )
        python_config["style"] = style

        # Optional field handling
        python_config["use_optional"] = Confirm.ask(
            "Use type unions (T | None) for optional fields?", default=True
        )

        # Style-specific configuration
        if style == "dataclass":
            python_config.update(self._configure_dataclass(console))
        elif style == "pydantic":
            python_config.update(self._configure_pydantic(console))
        elif style == "typeddict":
            python_config.update(self._configure_typeddict(console))

        return python_config

    def _configure_dataclass(self, console: Console) -> Dict[str, Any]:
        """Configure dataclass-specific options."""
        config = {}

        console.print("\n[cyan]Dataclass Options:[/cyan]")

        config["dataclass_slots"] = Confirm.ask(
            "Use __slots__ for memory optimization?", default=True
        )

        config["dataclass_frozen"] = Confirm.ask(
            "Make dataclasses immutable (frozen)?", default=False
        )

        config["dataclass_kw_only"] = Confirm.ask(
            "Require keyword-only arguments?", default=False
        )

        return config

    def _configure_pydantic(self, console: Console) -> Dict[str, Any]:
        """Configure Pydantic-specific options."""
        config = {}

        console.print("\n[cyan]Pydantic Options:[/cyan]")

        config["pydantic_use_field"] = Confirm.ask(
            "Use Field() for metadata?", default=True
        )

        if config["pydantic_use_field"]:
            config["pydantic_use_alias"] = Confirm.ask(
                "Generate field aliases for JSON keys?", default=True
            )

        config["pydantic_config_dict"] = Confirm.ask(
            "Generate model_config?", default=True
        )

        if config["pydantic_config_dict"]:
            config["pydantic_extra_forbid"] = Confirm.ask(
                "Forbid extra fields (strict mode)?", default=False
            )

        return config

    def _configure_typeddict(self, console: Console) -> Dict[str, Any]:
        """Configure TypedDict-specific options."""
        config = {}

        console.print("\n[cyan]TypedDict Options:[/cyan]")

        config["typeddict_total"] = Confirm.ask(
            "Make all fields required by default (total=True)?", default=False
        )

        return config

    def get_default_config(self) -> Dict[str, Any]:
        """Get default Python configuration for quick setup."""
        return {
            "style": "dataclass",
            "use_optional": True,
            "dataclass_slots": True,
            "dataclass_frozen": False,
            "dataclass_kw_only": False,
        }

    def show_advanced_features(self, console: Console) -> None:
        """Show advanced Python features and configuration options."""
        advanced_panel = Panel(
            """[bold]🚀 Advanced Python Features:[/bold]

[bold]Type System:[/bold]
• Modern unions: T | None instead of Optional[T]
• Generic collections: list[T], dict[K, V]
• NotRequired for TypedDict optional fields
• Forward references for recursive types

[bold]Dataclass Features:[/bold]
• __slots__ for memory efficiency
• frozen=True for immutability
• kw_only=True for better APIs
• field(default_factory=...) for mutable defaults

[bold]Pydantic v2 Features:[/bold]
• Field validation and constraints
• model_config for behavior control
• Field aliases for JSON mapping
• Custom validators and serializers

[bold]TypedDict Features:[/bold]
• Pure type hints (no runtime overhead)
• Compatible with structural typing
• NotRequired for optional fields (3.11+)
• Excellent mypy/pyright support

[bold]Code Quality:[/bold]
• PEP 8 compliant naming
• Proper docstrings
• Import organization
• Type hint completeness""",
            title="⚡ Advanced Configuration",
            border_style="purple",
        )

        console.print()
        console.print(advanced_panel)

    def validate_python_config(self, config: Dict[str, Any]) -> list[str]:
        """Validate Python-specific configuration and return warnings."""
        warnings = []

        style = config.get("style", "dataclass")

        # Style-specific validations
        if style == "dataclass":
            if config.get("dataclass_frozen") and not config.get("dataclass_slots"):
                warnings.append(
                    "Consider enabling slots with frozen for better performance"
                )

        elif style == "pydantic":
            if not config.get("pydantic_use_field"):
                warnings.append(
                    "Disabling Field() means no aliases or validation metadata"
                )

            if config.get("pydantic_extra_forbid"):
                warnings.append(
                    "extra='forbid' will reject any fields not in the model"
                )

        elif style == "typeddict":
            warnings.append(
                "TypedDict provides no runtime validation - consider Pydantic for validation"
            )

            if not config.get("use_optional"):
                warnings.append(
                    "TypedDict without NotRequired may cause type checking issues"
                )

        return warnings

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

    def show_style_comparison(self, console: Console) -> None:
        """Show comparison between Python styles."""
        comparison_panel = Panel(
            """[bold]📊 Style Comparison:[/bold]

[bold]Dataclass:[/bold]
✅ Standard library (no dependencies)
✅ Fast and lightweight
✅ Good IDE support
❌ No runtime validation
❌ Manual serialization

[bold]Pydantic:[/bold]
✅ Automatic validation
✅ JSON serialization built-in
✅ Extensive features
✅ Great for APIs
❌ External dependency
❌ Slightly slower

[bold]TypedDict:[/bold]
✅ Zero runtime overhead
✅ Pure type hints
✅ Perfect for mypy
✅ No dependencies
❌ No validation
❌ No serialization
❌ Limited features

[bold]Recommendations:[/bold]
• REST APIs: Pydantic
• Type checking: TypedDict
• Simple data: Dataclass
• Performance: Dataclass (frozen, slots)""",
            title="🔍 Which Style to Choose?",
            border_style="cyan",
        )

        console.print()
        console.print(comparison_panel)
