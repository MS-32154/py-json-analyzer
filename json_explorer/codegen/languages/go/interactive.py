"""
Go-specific interactive handler for code generation.

Provides Go-specific configuration options, templates, and information.
"""

from typing import Dict, Any, Optional

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm

from ...core.config import GeneratorConfig
from .config import get_web_api_config, get_strict_config, get_modern_config


class GoInteractiveHandler:
    """Interactive handler for Go-specific code generation options."""

    def get_language_info(self) -> Dict[str, str]:
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

    def get_template_choices(self) -> Dict[str, str]:
        """Get available Go configuration templates."""
        return {
            "web-api": "Optimized for REST API models with pointers for optional fields",
            "strict": "No pointers, strict types for high-performance code",
            "modern": "Uses modern Go features (Go 1.18+) with 'any' type",
        }

    def create_template_config(self, template_name: str) -> Optional[GeneratorConfig]:
        """Create configuration from Go template."""
        if template_name == "web-api":
            go_config = get_web_api_config()
            return GeneratorConfig(
                package_name="models",
                add_comments=True,
                generate_json_tags=True,
                json_tag_omitempty=True,
                language_config=go_config.__dict__,
            )

        elif template_name == "strict":
            go_config = get_strict_config()
            return GeneratorConfig(
                package_name="types",
                add_comments=True,
                generate_json_tags=True,
                json_tag_omitempty=False,
                language_config=go_config.__dict__,
            )

        elif template_name == "modern":
            go_config = get_modern_config()
            return GeneratorConfig(
                package_name="main",
                add_comments=True,
                generate_json_tags=True,
                json_tag_omitempty=True,
                language_config=go_config.__dict__,
            )

        return None

    def configure_language_specific(self, console: Console) -> Dict[str, Any]:
        """Handle Go-specific configuration options."""
        go_config = {}

        console.print("\n[bold]Go-Specific Options:[/bold]")

        # JSON tags
        go_config["generate_json_tags"] = Confirm.ask(
            "Generate JSON struct tags?", default=True
        )

        if go_config["generate_json_tags"]:
            go_config["json_tag_omitempty"] = Confirm.ask(
                "Add 'omitempty' to JSON tags?", default=True
            )
            go_config["json_tag_case"] = Prompt.ask(
                "JSON tag case style",
                choices=["original", "snake", "camel"],
                default="original",
            )

        # Optional fields
        go_config["use_pointers_for_optional"] = Confirm.ask(
            "Use pointers for optional fields?", default=True
        )

        # Type preferences
        if Confirm.ask("Configure type preferences?", default=False):
            go_config["int_type"] = Prompt.ask(
                "Integer type", choices=["int", "int32", "int64"], default="int64"
            )
            go_config["float_type"] = Prompt.ask(
                "Float type", choices=["float32", "float64"], default="float64"
            )

            # Modern Go features
            go_config["unknown_type"] = Prompt.ask(
                "Unknown type representation",
                choices=["interface{}", "any"],
                default="interface{}",
            )

        # Advanced options
        if Confirm.ask("Configure advanced options?", default=False):
            go_config["time_type"] = Prompt.ask(
                "Time type for timestamps",
                choices=["time.Time", "string", "int64"],
                default="time.Time",
            )

        return go_config

    def get_default_config(self) -> Dict[str, Any]:
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

    def show_advanced_features(self, console: Console) -> None:
        """Show advanced Go features and configuration options."""
        advanced_panel = Panel(
            """[bold]🚀 Advanced Go Features:[/bold]

[bold]Type Configuration:[/bold]
• Integer types: int, int32, int64
• Float types: float32, float64  
• Time handling: time.Time, string, int64
• Unknown types: interface{}, any (Go 1.18+)

[bold]JSON Tag Options:[/bold]
• Custom field names with case conversion
• Omitempty for optional fields
• Custom tag options and validation

[bold]Pointer Management:[/bold]
• Optional pointer usage for nullable fields
• Value types for performance-critical code
• Automatic nil-safety considerations

[bold]Code Generation Features:[/bold]
• Dependency-ordered struct generation
• Circular dependency detection
• Name conflict resolution
• Reserved word handling

[bold]Performance Considerations:[/bold]
• Zero-allocation struct generation
• Minimal pointer usage in strict mode
• Efficient memory layout optimization""",
            title="⚡ Advanced Configuration",
            border_style="purple",
        )

        console.print()
        console.print(advanced_panel)

    def validate_go_config(self, config: Dict[str, Any]) -> list[str]:
        """Validate Go-specific configuration and return warnings."""
        warnings = []

        # Check for potentially problematic combinations
        if not config.get("use_pointers_for_optional", True) and config.get(
            "json_tag_omitempty", True
        ):
            warnings.append(
                "Using omitempty without pointers may not work as expected for zero values"
            )

        # Check modern Go features
        if config.get("unknown_type") == "any" and config.get("int_type") == "int64":
            warnings.append(
                "Consider using 'int' with 'any' type for consistent modern Go style"
            )

        # Performance warnings
        if (
            config.get("use_pointers_for_optional", True)
            and "performance" in str(config.get("package_name", "")).lower()
        ):
            warnings.append(
                "Consider strict template for performance-critical packages"
            )

        return warnings

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
