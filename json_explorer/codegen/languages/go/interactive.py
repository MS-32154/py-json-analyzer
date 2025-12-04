"""
Go-specific interactive handler.

Provides Go-specific configuration options, templates, and examples
for the interactive code generation interface.
"""

from typing import Any

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm

from json_explorer.utils import prompt_input
from ...core.config import GeneratorConfig
from .config import get_web_api_config, get_strict_config, get_modern_config

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Go Interactive Handler
# ============================================================================


class GoInteractiveHandler:
    """Interactive handler for Go-specific code generation options."""

    __slots__ = ()

    def get_language_info(self) -> dict[str, str]:
        """Get Go-specific information for display."""
        return {
            "description": "Generates Go structs with JSON tags",
            "features": "Pointers, JSON tags, configurable types, modern Go support",
            "use_cases": "REST APIs, configuration, data models, JSON processing",
            "maturity": "Full support with multiple templates",
        }

    def show_configuration_examples(self, console: Console) -> None:
        """Show Go-specific configuration examples."""
        config_panel = Panel(
            """[bold]Go Configuration Examples:[/bold]

[green]Web API Template:[/green]
• Package: "models" 
• Pointers for optional fields
• JSON tags with omitempty
• int64 and float64 types

[green]Strict Template:[/green]  
• Package: "types"
• No pointers (value types only)
• JSON tags without omitempty
• High performance focus

[green]Modern Template:[/green]
• Uses Go 1.18+ features
• "any" instead of interface{}
• Modern type preferences

[bold]Key Go Features:[/bold]
• Configurable integer types (int, int32, int64)
• Optional pointer usage for optional fields
• JSON tag customization (omitempty, custom names)
• Time.Time support for timestamps
• Interface{} or 'any' for unknown types""",
            title="⚙️ Go Configuration Options",
            border_style="blue",
        )

        console.print()
        console.print(config_panel)

    def get_template_choices(self) -> dict[str, str]:
        """Get available Go configuration templates."""
        return {
            "web-api": "Optimized for REST API models with pointers",
            "strict": "No pointers, strict types for high-performance",
            "modern": "Uses modern Go features (Go 1.18+)",
        }

    def create_template_config(
        self,
        template_name: str,
    ) -> GeneratorConfig | None:
        """Create configuration from Go template."""
        match template_name:
            case "web-api":
                return GeneratorConfig(
                    package_name="models",
                    add_comments=True,
                    generate_json_tags=True,
                    json_tag_omitempty=True,
                    language_config=get_web_api_config().to_dict(),
                )

            case "strict":
                return GeneratorConfig(
                    package_name="types",
                    add_comments=True,
                    generate_json_tags=True,
                    json_tag_omitempty=False,
                    language_config=get_strict_config().to_dict(),
                )

            case "modern":
                return GeneratorConfig(
                    package_name="main",
                    add_comments=True,
                    generate_json_tags=True,
                    json_tag_omitempty=True,
                    language_config=get_modern_config().to_dict(),
                )

            case _:
                return None

    def configure_language_specific(
        self,
        console: Console,
    ) -> dict[str, Any]:
        """Handle Go-specific configuration options."""
        go_config = {}

        console.print("\n[bold]Go-Specific Options:[/bold]")

        # JSON tags
        go_config["generate_json_tags"] = Confirm.ask(
            "Generate JSON struct tags?",
            default=True,
        )

        if go_config["generate_json_tags"]:
            go_config["json_tag_omitempty"] = Confirm.ask(
                "Add 'omitempty' to JSON tags?",
                default=True,
            )
            go_config["json_tag_case"] = self._input(
                "JSON tag case style",
                choices=["original", "snake", "camel"],
                default="original",
                console=console,
            )

        # Optional fields
        go_config["use_pointers_for_optional"] = Confirm.ask(
            "Use pointers for optional fields?",
            default=True,
        )

        # Type preferences
        if Confirm.ask("Configure type preferences?", default=False):
            go_config["int_type"] = self._input(
                "Integer type",
                choices=["int", "int32", "int64"],
                default="int64",
                console=console,
            )
            go_config["float_type"] = self._input(
                "Float type",
                choices=["float32", "float64"],
                default="float64",
                console=console,
            )
            go_config["unknown_type"] = self._input(
                "Unknown type representation",
                choices=["interface{}", "any"],
                default="interface{}",
                console=console,
            )

        # Advanced options
        if Confirm.ask("Configure advanced options?", default=False):
            go_config["time_type"] = self._input(
                "Time type for timestamps",
                choices=["time.Time", "string", "int64"],
                default="time.Time",
                console=console,
            )

        logger.info(f"Go-specific config collected: {len(go_config)} options")
        return go_config

    def get_default_config(self) -> dict[str, Any]:
        """Get default Go configuration for quick setup."""
        return {
            "generate_json_tags": True,
            "json_tag_omitempty": True,
            "use_pointers_for_optional": True,
            "int_type": "int64",
            "float_type": "float64",
            "time_type": "time.Time",
            "unknown_type": "interface{}",
        }

    def show_examples(self, console: Console) -> None:
        """Show Go code generation examples."""
        examples_panel = Panel(
            """[bold]📝 Go Generation Examples:[/bold]

[bold]Input JSON:[/bold]
```json
{
  "user_id": 123,
  "name": "John",
  "email": null,
  "settings": {
    "theme": "dark"
  }
}
```

[bold]Generated Go (Web API template):[/bold]
```go
type Root struct {
    UserID   int64      `json:"user_id"`
    Name     string     `json:"name"`
    Email    *string    `json:"email,omitempty"`
    Settings *Settings  `json:"settings,omitempty"`
}

type Settings struct {
    Theme string `json:"theme"`
}
```

[bold]Generated Go (Strict template):[/bold]
```go
type Root struct {
    UserID   int64    `json:"user_id"`
    Name     string   `json:"name"`  
    Email    string   `json:"email"`
    Settings Settings `json:"settings"`
}
```""",
            title="🎯 Code Examples",
            border_style="green",
        )

        console.print()
        console.print(examples_panel)

    def validate_config(self, config: dict[str, Any]) -> list[str]:
        """
        Validate Go-specific configuration.

        Args:
            config: Configuration dictionary to validate

        Returns:
            List of warning messages (empty if valid)
        """
        warnings = []

        # Check for potentially problematic combinations
        if not config.get("use_pointers_for_optional", True):
            if config.get("json_tag_omitempty", True):
                warnings.append(
                    "Using omitempty without pointers may not work as expected for zero values"
                )

        # Check modern Go features
        if config.get("unknown_type") == "any":
            if config.get("int_type") == "int64":
                warnings.append(
                    "Consider using 'int' with 'any' type for consistent modern Go style"
                )

        # Performance warnings
        if config.get("use_pointers_for_optional", True):
            package_name = config.get("package_name", "")
            if "performance" in package_name.lower():
                warnings.append(
                    "Consider strict template for performance-critical packages"
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
