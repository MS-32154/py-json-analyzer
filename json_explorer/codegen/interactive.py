"""
Interactive code generation handler.

Provides language-agnostic interactive interface for code generation
with delegation to language-specific handlers for customization.
"""

from pathlib import Path
from typing import Any, Protocol

from rich.console import Console
from rich.panel import Panel
from rich.prompt import Confirm, Prompt
from rich.syntax import Syntax
from rich.table import Table
from rich import box

from . import (
    GeneratorError,
    generate_from_analysis,
    get_language_info,
    list_all_language_info,
    list_supported_languages,
    load_config,
)
from json_explorer.analyzer import analyze_json
from json_explorer.utils import prompt_input, prompt_input_path

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


# ============================================================================
# Language Handler Protocol
# ============================================================================


class LanguageInteractiveHandler(Protocol):
    """Protocol for language-specific interactive handlers."""

    def get_language_info(self) -> dict[str, str]:
        """Get language-specific information for display."""
        ...

    def show_configuration_examples(self, console: Console) -> None:
        """Show language-specific configuration examples."""
        ...

    def get_template_choices(self) -> dict[str, str]:
        """Get available configuration templates."""
        ...

    def create_template_config(self, template_name: str) -> Any:
        """Create configuration from template."""
        ...

    def configure_language_specific(self, console: Console) -> dict[str, Any]:
        """Handle language-specific configuration options."""
        ...

    def get_default_config(self) -> dict[str, Any]:
        """Get default configuration for quick setup."""
        ...


# ============================================================================
# Main Interactive Handler
# ============================================================================


class CodegenInteractiveHandler:
    """Interactive handler for code generation."""

    def __init__(self, data: Any, console: Console | None = None):
        """
        Initialize the codegen interactive handler.

        Args:
            data: JSON data to generate code for
            console: Rich console instance (creates new if None)
        """
        self.data = data
        self.console = console or Console()
        self._analysis_cache: dict | None = None
        self._language_handlers: dict[str, LanguageInteractiveHandler] = {}

        logger.info("CodegenInteractiveHandler initialized")

    def run_interactive(self) -> bool:
        """
        Run the interactive code generation interface.

        Returns:
            True if successful, False if cancelled or error
        """
        if not self.data:
            self.console.print("[red]⚠️ No data available for code generation[/red]")
            return False

        try:
            while True:
                action = self._show_main_menu()

                match action:
                    case "back":
                        logger.info("User exited code generation")
                        return True
                    case "generate":
                        self._interactive_generation()
                    case "languages":
                        self._show_languages_menu()
                    case "info":
                        self._show_general_info()
                    case "templates":
                        self._show_templates_menu()

        except KeyboardInterrupt:
            self.console.print("\n[yellow]👋 Code generation cancelled[/yellow]")
            logger.info("Code generation cancelled by user")
            return False
        except Exception as e:
            self.console.print(f"[red]⚠️ Unexpected error: {e}[/red]")
            logger.exception("Unexpected error in interactive handler")
            return False

    # ========================================================================
    # prompt_toolkit integration
    # ========================================================================

    def _input(self, message: str, default: str | None = None, **kwargs) -> str:
        return prompt_input(
            message,
            default=default,
            choices=kwargs.get("choices"),
            console=self.console,
        )

    def _input_path(self, message: str, default: str = "") -> str:
        return prompt_input_path(message, default=default)

    # ========================================================================
    # Main Menu
    # ========================================================================

    def _show_main_menu(self) -> str:
        """Show the main codegen menu and get user choice."""
        menu_panel = Panel.fit(
            """[bold blue]⚡ Code Generation Menu[/bold blue]

[cyan]1.[/cyan] 🚀 Generate Code
[cyan]2.[/cyan] 📋 Available Languages
[cyan]3.[/cyan] 📖 General Information
[cyan]4.[/cyan] 🎨 Configuration Templates
[cyan]b.[/cyan] 🔙 Back to Main Menu""",
            border_style="blue",
            title="⚡ Code Generator",
        )

        self.console.print()
        self.console.print(menu_panel)

        choice = Prompt.ask(
            "\n[bold]Choose an option[/bold]",
            choices=["1", "2", "3", "4", "b"],
            default="1",
        )

        choice_map = {
            "1": "generate",
            "2": "languages",
            "3": "info",
            "4": "templates",
            "b": "back",
        }

        return choice_map.get(choice, "back")

    # ========================================================================
    # Code Generation Flow
    # ========================================================================

    def _interactive_generation(self) -> None:
        """Handle the interactive code generation process."""
        try:
            # Step 1: Language selection
            language = self._select_language()
            if not language:
                return

            logger.info(f"User selected language: {language}")

            # Step 2: Configuration
            config = self._configure_generation(language)
            if not config:
                return

            # Step 3: Root name
            root_name = self._input("Root structure name", default="Root")

            # Step 4: Generate
            result = self._generate_code(language, config, root_name)
            if not result:
                return

            # Step 5: Handle output
            self._handle_generation_output(result, language, root_name)

        except GeneratorError as e:
            self.console.print(f"[red]⚠️ Generation error:[/red] {e}")
            logger.error(f"Generation error: {e}")
        except Exception as e:
            self.console.print(f"[red]⚠️ Unexpected error:[/red] {e}")
            logger.exception("Unexpected error during generation")

    def _select_language(self) -> str | None:
        """Interactive language selection."""
        languages = list_supported_languages()

        if not languages:
            self.console.print("[red]⚠️ No code generators available[/red]")
            return None

        self.console.print("\n[bold]📋 Available Languages:[/bold]")

        for i, lang in enumerate(languages, 1):
            self.console.print(f"  [cyan]{i}.[/cyan] {lang}")

        self.console.print(f"  [cyan]i.[/cyan] Show detailed info")
        self.console.print(f"  [cyan]b.[/cyan] Back")

        choice = Prompt.ask(
            "\n[bold]Select language[/bold]",
            choices=[str(i) for i in range(1, len(languages) + 1)] + ["i", "b"],
            default="1",
        )

        match choice:
            case "b":
                return None
            case "i":
                self._show_detailed_language_info()
                return self._select_language()
            case _:
                return languages[int(choice) - 1]

    def _configure_generation(self, language: str) -> dict | None:
        """Interactive configuration for code generation."""
        self.console.print(f"\n⚙️ [bold]Configure {language.title()} Generation[/bold]")

        config_type = self._input(
            "Configuration approach",
            choices=["quick", "custom", "template", "file"],
            default="quick",
        )

        match config_type:
            case "quick":
                return self._quick_configuration(language)
            case "custom":
                return self._custom_configuration(language)
            case "template":
                return self._template_configuration(language)
            case "file":
                return self._file_configuration()
            case _:
                return None

    def _quick_configuration(self, language: str) -> dict:
        """Quick configuration with sensible defaults."""
        config_dict = {
            "package_name": self._input("Package/namespace name", default="main"),
            "add_comments": Confirm.ask("Generate comments?", default=True),
        }

        # Get language-specific defaults
        lang_handler = self._get_language_handler(language)
        if lang_handler:
            lang_defaults = lang_handler.get_default_config()
            config_dict.update(lang_defaults)

        logger.debug(f"Quick config created: {len(config_dict)} options")
        return config_dict

    def _custom_configuration(self, language: str) -> dict:
        """Detailed custom configuration."""
        config_dict = {}

        # Basic configuration
        config_dict["package_name"] = self._input(
            "Package/namespace name",
            default="main",
        )
        config_dict["add_comments"] = Confirm.ask(
            "Generate comments/documentation?",
            default=True,
        )

        # Naming conventions
        if Confirm.ask("Configure naming conventions?", default=False):
            config_dict["struct_case"] = self._input(
                "Struct/class name case",
                choices=["pascal", "camel", "snake"],
                default="pascal",
            )
            config_dict["field_case"] = self._input(
                "Field name case",
                choices=["pascal", "camel", "snake"],
                default="pascal",
            )

        # Language-specific configuration
        lang_handler = self._get_language_handler(language)
        if lang_handler:
            lang_config = lang_handler.configure_language_specific(self.console)
            config_dict.update(lang_config)

        logger.debug(f"Custom config created: {len(config_dict)} options")
        return config_dict

    def _template_configuration(self, language: str) -> dict | None:
        """Use configuration templates."""
        self.console.print(
            f"\n🎨 [bold]Configuration Templates for {language.title()}[/bold]"
        )

        lang_handler = self._get_language_handler(language)
        if not lang_handler:
            self.console.print(
                f"[yellow]No templates available for {language} yet[/yellow]"
            )
            return self._custom_configuration(language)

        templates = lang_handler.get_template_choices()
        if not templates:
            self.console.print(f"[yellow]No templates defined for {language}[/yellow]")
            return self._custom_configuration(language)

        # Show templates
        for name, desc in templates.items():
            self.console.print(f"  [green]•[/green] [bold]{name}[/bold]: {desc}")

        # Add custom option
        choices = list(templates.keys()) + ["custom", "back"]
        template = self._input(
            f"\nSelect {language} template",
            choices=choices,
            default=list(templates.keys())[0] if templates else "custom",
        )

        match template:
            case "back":
                return None
            case "custom":
                return self._custom_configuration(language)
            case _:
                config = lang_handler.create_template_config(template)
                if config:
                    self._show_template_info(template, templates[template])
                    # Convert GeneratorConfig to dict if needed
                    if hasattr(config, "to_dict"):
                        return config.to_dict()
                return config

    def _show_template_info(self, template_name: str, description: str) -> None:
        """Show information about selected template."""
        info_panel = Panel(
            f"[bold]Selected Template: {template_name}[/bold]\n\n{description}",
            border_style="green",
            title="✅ Template Applied",
        )
        self.console.print()
        self.console.print(info_panel)

    def _file_configuration(self) -> dict | None:
        """Load configuration from file."""
        config_file = self._input_path(
            "Configuration file path",
            default="codegen_config.json",
        )

        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self.console.print(
                    f"[red]⚠️ Configuration file not found: {config_path}[/red]"
                )
                return None

            config = load_config(config_file=config_path)
            self.console.print(
                f"[green]✅ Configuration loaded from: {config_path}[/green]"
            )

            # Convert to dict
            if hasattr(config, "to_dict"):
                return config.to_dict()
            return config

        except Exception as e:
            self.console.print(f"[red]⚠️ Error loading configuration: {e}[/red]")
            logger.error(f"Failed to load config file: {e}")
            return None

    def _generate_code(
        self,
        language: str,
        config: dict,
        root_name: str,
    ) -> Any:
        """Generate code and handle errors."""
        try:
            self.console.print(f"\n⚡ [yellow]Generating {language} code...[/yellow]")

            # Use cached analysis or create new one
            if self._analysis_cache is None:
                self._analysis_cache = analyze_json(self.data)
                logger.debug("JSON analyzed and cached")

            result = generate_from_analysis(
                self._analysis_cache,
                language,
                config,
                root_name,
            )

            if not result.success:
                self.console.print(
                    f"[red]⚠️ Generation failed:[/red] {result.error_message}"
                )
                return None

            self.console.print("[green]✅ Code generation completed![/green]")
            logger.info("Code generation completed successfully")
            return result

        except GeneratorError as e:
            self.console.print(f"[red]⚠️ Generator error:[/red] {e}")
            logger.error(f"Generator error: {e}")
            return None
        except Exception as e:
            self.console.print(f"[red]⚠️ Unexpected error during generation:[/red] {e}")
            logger.exception("Unexpected error during generation")
            return None

    # ========================================================================
    # Output Handling
    # ========================================================================

    def _handle_generation_output(
        self,
        result: Any,
        language: str,
        root_name: str,
    ) -> None:
        """Handle the output of generated code."""
        # Display warnings first
        if result.warnings:
            self._display_warnings(result.warnings)

        # Show generation metadata
        if result.metadata:
            self._display_metadata(result.metadata)

        # Main output handling
        action = self._input(
            "\nWhat would you like to do with the generated code?",
            choices=["preview", "save", "both", "regenerate"],
            default="preview",
        )

        match action:
            case "preview":
                self._preview_code(result.code, language)
                if Confirm.ask("\nSave the generated code to file?", default=True):
                    self._save_code(result.code, language, root_name)

            case "save":
                self._save_code(result.code, language, root_name)

            case "both":
                self._preview_code(result.code, language)
                self._save_code(result.code, language, root_name)

            case "regenerate":
                self._interactive_generation()

    def _preview_code(self, code: str, language: str) -> None:
        """Preview generated code with syntax highlighting."""
        self.console.print(
            f"\n[green]📄 Generated {language.title()} Code Preview[/green]"
        )

        try:
            # Map language names for syntax highlighting
            syntax_lang = language.lower()
            if syntax_lang == "golang":
                syntax_lang = "go"
            elif syntax_lang == "py":
                syntax_lang = "python"

            syntax = Syntax(
                code,
                syntax_lang,
                theme="monokai",
                line_numbers=False,
                padding=1,
            )
            self.console.print()
            self.console.print(syntax)
            self.console.print()

        except Exception:
            # Fallback to plain text
            self.console.print("[dim]" + code + "[/dim]")

    def _save_code(self, code: str, language: str, root_name: str) -> None:
        """Save generated code to file."""
        try:
            # Get language info for file extension
            lang_info = get_language_info(language)
            extension = lang_info["file_extension"]

            # Suggest filename
            default_filename = f"{root_name.lower()}{extension}"
            filename = self._input_path("Save as", default=default_filename)

            # Ensure proper extension
            if not filename.endswith(extension):
                filename += extension

            # Save file
            output_path = Path(filename)

            # Check if file exists
            if output_path.exists():
                if not Confirm.ask(
                    f"File {output_path} exists. Overwrite?",
                    default=False,
                ):
                    filename = self._input_path("Enter new filename")
                    output_path = Path(filename)

            output_path.write_text(code, encoding="utf-8")
            self.console.print(
                f"[green]✅ Code saved to:[/green] [cyan]{output_path}[/cyan]"
            )
            logger.info(f"Code saved to: {output_path}")

        except Exception as e:
            self.console.print(f"[red]⚠️ Error saving file:[/red] {e}")
            logger.error(f"Failed to save file: {e}")

    def _display_warnings(self, warnings: list[str]) -> None:
        """Display generation warnings."""
        self.console.print("\n[yellow]⚠️ Warnings:[/yellow]")
        for warning in warnings:
            self.console.print(f"  [yellow]•[/yellow] {warning}")

    def _display_metadata(self, metadata: dict[str, Any]) -> None:
        """Display generation metadata."""
        metadata_table = Table(
            title="📊 Generation Summary",
            box=box.SIMPLE,
            show_header=True,
            header_style="bold cyan",
        )

        metadata_table.add_column("Property", style="bold")
        metadata_table.add_column("Value", style="green")

        for key, value in metadata.items():
            display_key = key.replace("_", " ").title()
            metadata_table.add_row(display_key, str(value))

        self.console.print()
        self.console.print(metadata_table)

    # ========================================================================
    # Information Displays
    # ========================================================================

    def _show_languages_menu(self) -> None:
        """Show detailed languages information menu."""
        while True:
            choice = self._input(
                "\n[bold]Language Information[/bold]",
                choices=["list", "details", "specific", "back"],
                default="list",
            )

            match choice:
                case "back":
                    break
                case "list":
                    self._show_language_list()
                case "details":
                    self._show_detailed_language_info()
                case "specific":
                    self._show_specific_language_info()

    def _show_language_list(self) -> None:
        """Show simple language list."""
        languages = list_supported_languages()

        self.console.print("\n[bold]📋 Supported Languages:[/bold]")
        for lang in languages:
            self.console.print(f"  [green]•[/green] {lang}")

    def _show_detailed_language_info(self) -> None:
        """Show detailed information about all languages."""
        try:
            language_info = list_all_language_info()

            if not language_info:
                self.console.print("[yellow]⚠️ No generators available[/yellow]")
                return

            table = Table(
                title="🔧 Detailed Language Information",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )

            table.add_column("Language", style="bold green", no_wrap=True)
            table.add_column("Extension", style="cyan", no_wrap=True)
            table.add_column("Generator Class", style="dim", no_wrap=True)
            table.add_column("Aliases", style="blue")

            for lang_name, info in sorted(language_info.items()):
                aliases = (
                    ", ".join(info["aliases"]) if info["aliases"] else "[dim]none[/dim]"
                )

                table.add_row(
                    f"🔧 {lang_name}",
                    info["file_extension"],
                    info["class"],
                    aliases,
                )

            self.console.print()
            self.console.print(table)

        except Exception as e:
            self.console.print(f"[red]Error loading language info: {e}[/red]")
            logger.error(f"Failed to load language info: {e}")

    def _show_specific_language_info(self) -> None:
        """Show information about a specific language."""
        languages = list_supported_languages()

        if not languages:
            self.console.print("[red]No languages available[/red]")
            return

        language = self._input(
            "Select language for detailed info",
            choices=languages + ["back"],
            default=languages[0],
        )

        if language == "back":
            return

        try:
            info = get_language_info(language)
            self._display_specific_language_info(language, info)
        except Exception as e:
            self.console.print(f"[red]Error getting language info: {e}[/red]")
            logger.error(f"Failed to get language info: {e}")

    def _display_specific_language_info(
        self,
        language: str,
        info: dict[str, Any],
    ) -> None:
        """Display detailed information about a specific language."""
        info_panel = Panel(
            f"""[bold]Language:[/bold] {info['name']}
[bold]File Extension:[/bold] {info['file_extension']}
[bold]Generator Class:[/bold] {info['class']}
[bold]Module:[/bold] {info['module']}
[bold]Aliases:[/bold] {', '.join(info['aliases']) if info['aliases'] else 'none'}""",
            title=f"🔧 {info['name'].title()} Generator Info",
            border_style="green",
        )

        self.console.print()
        self.console.print(info_panel)

        # Show language-specific information
        lang_handler = self._get_language_handler(language)
        if lang_handler:
            lang_handler.show_configuration_examples(self.console)

    def _show_general_info(self) -> None:
        """Show general code generation information."""
        info_panel = Panel(
            """[bold blue]📖 Code Generation Overview[/bold blue]

[bold]What it does:[/bold]
• Analyzes JSON data structure
• Generates strongly-typed data structures  
• Supports multiple programming languages
• Handles nested objects and arrays
• Preserves field names and types
• Detects optional vs required fields

[bold]Key Features:[/bold]
• Smart type detection and conflict resolution
• Configurable naming conventions (PascalCase, camelCase, snake_case)
• JSON serialization tags and annotations
• Template-based generation for consistency
• Custom configuration profiles
• Detailed validation and warnings

[bold]Current Status:[/bold]
• Go - Full support with multiple templates ✅
• Python - Full support (dataclass, pydantic, typeddict) ✅
• TypeScript - Coming soon 🚧  
• Rust - Coming soon 🚧

[bold]Use Cases:[/bold]
• API client/server model generation
• Configuration file structures
• Data transfer objects (DTOs)
• Database schema representations
• Type-safe JSON processing""",
            border_style="blue",
        )

        self.console.print()
        self.console.print(info_panel)

    def _show_templates_menu(self) -> None:
        """Show configuration templates information."""
        languages = list_supported_languages()

        if not languages:
            self.console.print("[red]No languages available[/red]")
            return

        self.console.print("\n[bold blue]🎨 Configuration Templates[/bold blue]")

        for language in languages:
            lang_handler = self._get_language_handler(language)
            if lang_handler:
                templates = lang_handler.get_template_choices()
                if templates:
                    self.console.print(f"\n[bold]{language.title()} Templates:[/bold]")
                    for template_name, description in templates.items():
                        self.console.print(
                            f"  [green]•[/green] {template_name}: {description}"
                        )
            else:
                self.console.print(
                    f"\n[yellow]{language.title()}: No templates available[/yellow]"
                )

    # ========================================================================
    # Language Handler Management
    # ========================================================================

    def _get_language_handler(
        self,
        language: str,
    ) -> LanguageInteractiveHandler | None:
        """Get language-specific interactive handler."""
        # Check cache
        if language in self._language_handlers:
            return self._language_handlers[language]

        try:
            # Try to import language-specific handler
            module_name = (
                f"json_explorer.codegen.languages.{language.lower()}.interactive"
            )
            module = __import__(module_name, fromlist=[""])

            # Look for handler class
            handler_class_name = f"{language.title()}InteractiveHandler"
            if hasattr(module, handler_class_name):
                handler_class = getattr(module, handler_class_name)
                handler = handler_class()
                self._language_handlers[language] = handler
                logger.debug(f"Loaded interactive handler for {language}")
                return handler

        except ImportError:
            logger.debug(f"No interactive handler available for {language}")
        except Exception as e:
            logger.warning(f"Failed to load handler for {language}: {e}")

        return None
