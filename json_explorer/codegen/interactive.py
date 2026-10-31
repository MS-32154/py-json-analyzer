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

from json_explorer.analyzer import Node, analyze_json
from json_explorer.codegen.registry import get_plugin
from json_explorer.logging_config import get_logger
from json_explorer.ui import ask, ask_path, print_metadata

from . import (
    GeneratorConfig,
    GeneratorError,
    generate_from_analysis,
    get_language_info,
    list_languages,
    load_config,
)

logger = get_logger(__name__)


# ============================================================================
# Language Handler Protocol
# ============================================================================


class LanguageInteractiveHandler(Protocol):
    """Protocol for language-specific interactive handlers."""

    def get_template_choices(self) -> dict[str, str]:
        """Get available configuration templates."""
        ...

    def create_template_config(self, template_name: str) -> GeneratorConfig | None:
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
        self._analysis_cache: Node | None = None
        self._language_handlers: dict[str, LanguageInteractiveHandler] = {}

        logger.info("CodegenInteractiveHandler initialized")

    def run_interactive(self) -> bool:
        """
        Run the interactive code generation interface.

        Returns:
            True if successful, False if cancelled or error
        """
        if self.data is None:
            self.console.print("[red]⚠️ No data available for code generation[/red]")
            return False

        try:
            while True:
                self._interactive_generation()
                if not Confirm.ask("\nGenerate more code?", default=False):
                    return True

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

    def _interactive_generation(self) -> None:
        """Handle the interactive code generation process."""
        try:
            # Step 1: Language selection
            language = self._select_language()
            if not language:
                return

            logger.info("User selected language: %s", language)

            # Step 2: Configuration
            config = self._configure_generation(language)
            if not config:
                return

            # Step 3: Root name
            root_name = ask("Root structure name", default="Root")

            # Step 4: Generate
            result = self._generate_code(language, config, root_name)
            if not result:
                return

            # Step 5: Handle output
            self._handle_generation_output(result, language, root_name)

        except GeneratorError as e:
            self.console.print(f"[red]⚠️ Generation error:[/red] {e}")
            logger.debug("Generation error: %s", e)
        except Exception as e:
            self.console.print(f"[red]⚠️ Unexpected error:[/red] {e}")
            logger.exception("Unexpected error during generation")

    def _select_language(self) -> str | None:
        """Interactive language selection."""
        languages = list_languages()

        if not languages:
            self.console.print("[red]⚠️ No code generators available[/red]")
            return None

        self.console.print("\n[bold]📋 Available Languages:[/bold]")

        for i, lang in enumerate(languages, 1):
            self.console.print(f"  [cyan]{i}.[/cyan] {lang}")

        self.console.print("  [cyan]b.[/cyan] Back")

        choice = Prompt.ask(
            "\n[bold]Select language[/bold]",
            choices=[str(i) for i in range(1, len(languages) + 1)] + ["b"],
            default="1",
        )

        match choice:
            case "b":
                return None
            case _:
                return languages[int(choice) - 1]

    def _configure_generation(self, language: str) -> dict | None:
        """Interactive configuration for code generation."""
        self.console.print(f"\n⚙️ [bold]Configure {language.title()} Generation[/bold]")

        config_type = ask(
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
            "package_name": ask("Package/namespace name", default="main"),
            "add_comments": Confirm.ask("Generate comments?", default=True),
        }

        # Get language-specific defaults
        lang_handler = self._get_language_handler(language)
        if lang_handler:
            lang_defaults = lang_handler.get_default_config()
            config_dict.update(lang_defaults)

        logger.debug("Quick config created: %s options", len(config_dict))
        return config_dict

    def _custom_configuration(self, language: str) -> dict:
        """Detailed custom configuration."""
        config_dict: dict[str, Any] = {}

        # Basic configuration
        config_dict["package_name"] = ask(
            "Package/namespace name",
            default="main",
        )
        config_dict["add_comments"] = Confirm.ask(
            "Generate comments/documentation?",
            default=True,
        )

        # Language-specific configuration
        lang_handler = self._get_language_handler(language)
        if lang_handler:
            lang_config = lang_handler.configure_language_specific(self.console)
            config_dict.update(lang_config)

        logger.debug("Custom config created: %s options", len(config_dict))
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
        choices = [*list(templates.keys()), "custom", "back"]
        template = ask(
            f"\nSelect {language} template",
            choices=choices,
            default=next(iter(templates.keys())) if templates else "custom",
        )

        match template:
            case "back":
                return None
            case "custom":
                return self._custom_configuration(language)
            case _:
                config = lang_handler.create_template_config(template)
                if config is None:
                    return None
                self._show_template_info(template, templates[template])
                return config.to_dict()

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
        config_file = ask_path(
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

            return config.to_dict()

        except Exception as e:
            self.console.print(f"[red]⚠️ Error loading configuration: {e}[/red]")
            logger.debug("Failed to load config file: %s", e)
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
            logger.debug("Generator error: %s", e)
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
            print_metadata(self.console, result.metadata, "📊 Generation Summary")

        # Main output handling
        action = ask(
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
            filename = ask_path("Save as", default=default_filename)

            # Ensure proper extension
            if not filename.endswith(extension):
                filename += extension

            # Save file
            output_path = Path(filename)

            # Check if file exists
            if output_path.exists() and not Confirm.ask(
                f"File {output_path} exists. Overwrite?",
                default=False,
            ):
                filename = ask_path("Enter new filename")
                output_path = Path(filename)

            output_path.write_text(code, encoding="utf-8")
            self.console.print(
                f"[green]✅ Code saved to:[/green] [cyan]{output_path}[/cyan]"
            )
            logger.info("Code saved to: %s", output_path)

        except Exception as e:
            self.console.print(f"[red]⚠️ Error saving file:[/red] {e}")
            logger.debug("Failed to save file: %s", e)

    def _display_warnings(self, warnings: list[str]) -> None:
        """Display generation warnings."""
        self.console.print("\n[yellow]⚠️ Warnings:[/yellow]")
        for warning in warnings:
            self.console.print(f"  [yellow]•[/yellow] {warning}")

    def _get_language_handler(
        self,
        language: str,
    ) -> LanguageInteractiveHandler | None:
        """Get language-specific interactive handler."""
        if language not in self._language_handlers:
            plugin = get_plugin(language)
            if plugin.interactive is None:
                return None
            self._language_handlers[language] = plugin.interactive()
        return self._language_handlers[language]
