"""
Interactive code generation handler - Language agnostic base.

Provides the main interactive interface for code generation with
delegation to language-specific handlers for customization.
"""

from pathlib import Path
from typing import Dict, Any, Optional, Protocol

from rich.console import Console
from rich.prompt import Prompt, Confirm
from rich.panel import Panel
from rich.table import Table
from rich.syntax import Syntax
from rich import box

from . import (
    generate_from_analysis,
    list_supported_languages,
    get_language_info,
    list_all_language_info,
    GeneratorConfig,
    load_config,
    GeneratorError,
)
from json_explorer.analyzer import analyze_json


class LanguageInteractiveHandler(Protocol):
    """Protocol for language-specific interactive handlers."""

    def get_language_info(self) -> Dict[str, str]:
        """Get language-specific information for display."""
        ...

    def show_configuration_examples(self, console: Console) -> None:
        """Show language-specific configuration examples."""
        ...

    def get_template_choices(self) -> Dict[str, str]:
        """Get available configuration templates."""
        ...

    def create_template_config(self, template_name: str) -> Optional[GeneratorConfig]:
        """Create configuration from template."""
        ...

    def configure_language_specific(self, console: Console) -> Dict[str, Any]:
        """Handle language-specific configuration options."""
        ...

    def get_default_config(self) -> Dict[str, Any]:
        """Get default configuration for quick setup."""
        ...


class CodegenInteractiveHandler:
    """Interactive handler for code generation."""

    def __init__(self, data: Any, console: Console = None):
        """
        Initialize the codegen interactive handler.

        Args:
            data: JSON data to generate code for
            console: Rich console instance (creates new if None)
        """
        self.data = data
        self.console = console or Console()
        self._analysis_cache = None  # Cache analysis result
        self._language_handlers = {}  # Cache for language handlers

    def run_interactive(self) -> bool:
        """
        Run the interactive code generation interface.

        Returns:
            True if successful, False if user cancelled or error occurred
        """
        if not self.data:
            self.console.print("[red]⚠ No data available for code generation[/red]")
            return False

        try:
            while True:
                action = self._show_main_menu()

                if action == "back":
                    return True
                elif action == "generate":
                    self._interactive_generation()
                elif action == "languages":
                    self._show_languages_menu()
                elif action == "info":
                    self._show_general_info()
                elif action == "templates":
                    self._show_templates_menu()

        except KeyboardInterrupt:
            self.console.print("\n[yellow]👋 Code generation cancelled[/yellow]")
            return False
        except Exception as e:
            self.console.print(f"[red]⚠ Unexpected error: {e}[/red]")
            return False

    def _show_main_menu(self) -> str:
        """Show the main codegen menu and get user choice."""
        menu_panel = Panel.fit(
            """[bold blue]⚡ Code Generation Menu[/bold blue]

[cyan]1.[/cyan] 🚀 Generate Code
[cyan]2.[/cyan] 📋 Available Languages
[cyan]3.[/cyan] 📖 General Information
[cyan]4.[/cyan] 🎨 Configuration Templates
[cyan]b.[/cyan] 📙 Back to Main Menu""",
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

    def _interactive_generation(self):
        """Handle the interactive code generation process."""
        try:
            # Step 1: Language selection
            language = self._select_language()
            if not language:
                return

            # Step 2: Configuration
            config = self._configure_generation(language)
            if not config:
                return

            # Step 3: Root name
            root_name = Prompt.ask("Root structure name", default="Root")

            # Step 4: Generate
            result = self._generate_code(language, config, root_name)
            if not result:
                return

            # Step 5: Handle output
            self._handle_generation_output(result, language, root_name)

        except GeneratorError as e:
            self.console.print(f"[red]⚠ Generation error:[/red] {e}")
        except Exception as e:
            self.console.print(f"[red]⚠ Unexpected error:[/red] {e}")

    def _select_language(self) -> Optional[str]:
        """Interactive language selection."""
        languages = list_supported_languages()

        if not languages:
            self.console.print("[red]⚠ No code generators available[/red]")
            return None

        self.console.print(f"\n[bold]📋 Available Languages:[/bold]")

        # Show compact language list
        for i, lang in enumerate(languages, 1):
            self.console.print(f"  [cyan]{i}.[/cyan] {lang}")

        self.console.print(f"  [cyan]i.[/cyan] Show detailed info")
        self.console.print(f"  [cyan]b.[/cyan] Back")

        choice = Prompt.ask(
            "\n[bold]Select language[/bold]",
            choices=[str(i) for i in range(1, len(languages) + 1)] + ["i", "b"],
            default="1",
        )

        if choice == "b":
            return None
        elif choice == "i":
            self._show_detailed_language_info()
            return self._select_language()  # Recursive call after showing info
        else:
            return languages[int(choice) - 1]

    def _configure_generation(self, language: str) -> Optional[GeneratorConfig]:
        """Interactive configuration for code generation."""
        self.console.print(f"\n⚙️ [bold]Configure {language.title()} Generation[/bold]")

        config_type = Prompt.ask(
            "Configuration approach",
            choices=["quick", "custom", "template", "file"],
            default="quick",
        )

        if config_type == "quick":
            return self._quick_configuration(language)
        elif config_type == "custom":
            return self._custom_configuration(language)
        elif config_type == "template":
            return self._template_configuration(language)
        elif config_type == "file":
            return self._file_configuration()

        return None

    def _quick_configuration(self, language: str) -> GeneratorConfig:
        """Quick configuration with sensible defaults."""
        config_dict = {
            "package_name": Prompt.ask("Package/namespace name", default="main"),
            "add_comments": Confirm.ask("Generate comments?", default=True),
        }

        # Get language-specific defaults
        lang_handler = self._get_language_handler(language)
        if lang_handler:
            lang_defaults = lang_handler.get_default_config()
            config_dict.update(lang_defaults)

        return load_config(custom_config=config_dict)

    def _custom_configuration(self, language: str) -> GeneratorConfig:
        """Detailed custom configuration."""
        config_dict = {}

        # Basic configuration
        config_dict["package_name"] = Prompt.ask(
            "Package/namespace name", default="main"
        )
        config_dict["add_comments"] = Confirm.ask(
            "Generate comments/documentation?", default=True
        )

        # Naming conventions
        if Confirm.ask("Configure naming conventions?", default=False):
            config_dict["struct_case"] = Prompt.ask(
                "Struct/class name case",
                choices=["pascal", "camel", "snake"],
                default="pascal",
            )
            config_dict["field_case"] = Prompt.ask(
                "Field name case",
                choices=["pascal", "camel", "snake"],
                default="pascal",
            )

        # Language-specific configuration
        lang_handler = self._get_language_handler(language)
        if lang_handler:
            lang_config = lang_handler.configure_language_specific(self.console)
            config_dict.update(lang_config)

        return load_config(custom_config=config_dict)

    def _template_configuration(self, language: str) -> Optional[GeneratorConfig]:
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

        # Add custom option
        choices = list(templates.keys()) + ["custom"]
        template = Prompt.ask(
            f"Select {language} template",
            choices=choices,
            default=list(templates.keys())[0],
        )

        if template == "custom":
            return self._custom_configuration(language)

        config = lang_handler.create_template_config(template)
        if config:
            self._show_template_info(template, templates[template])

        return config

    def _show_template_info(self, template_name: str, description: str):
        """Show information about selected template."""
        info_panel = Panel(
            f"[bold]Selected Template: {template_name}[/bold]\n\n{description}",
            border_style="green",
            title="✅ Template Applied",
        )
        self.console.print()
        self.console.print(info_panel)

    def _file_configuration(self) -> Optional[GeneratorConfig]:
        """Load configuration from file."""
        config_file = Prompt.ask(
            "Configuration file path", default="codegen_config.json"
        )

        try:
            config_path = Path(config_file)
            if not config_path.exists():
                self.console.print(
                    f"[red]⚠ Configuration file not found: {config_path}[/red]"
                )
                return None

            config = load_config(config_file=config_path)
            self.console.print(
                f"[green]✅ Configuration loaded from: {config_path}[/green]"
            )
            return config

        except Exception as e:
            self.console.print(f"[red]⚠ Error loading configuration: {e}[/red]")
            return None

    def _generate_code(self, language: str, config: GeneratorConfig, root_name: str):
        """Generate code and handle errors."""
        try:
            self.console.print(f"\n⚡ [yellow]Generating {language} code...[/yellow]")

            # Use cached analysis or create new one
            if self._analysis_cache is None:
                self._analysis_cache = analyze_json(self.data)

            result = generate_from_analysis(
                self._analysis_cache, language, config, root_name
            )

            if not result.success:
                self.console.print(
                    f"[red]⚠ Generation failed:[/red] {result.error_message}"
                )
                return None

            self.console.print("[green]✅ Code generation completed![/green]")
            return result

        except GeneratorError as e:
            self.console.print(f"[red]⚠ Generator error:[/red] {e}")
            return None
        except Exception as e:
            self.console.print(f"[red]⚠ Unexpected error during generation:[/red] {e}")
            return None

    def _handle_generation_output(self, result, language: str, root_name: str):
        """Handle the output of generated code."""
        # Display warnings first
        if result.warnings:
            self._display_warnings(result.warnings)

        # Show generation metadata
        if result.metadata:
            self._display_metadata(result.metadata)

        # Main output handling
        action = Prompt.ask(
            "\nWhat would you like to do with the generated code?",
            choices=["preview", "save", "both", "regenerate"],
            default="preview",
        )

        if action in ["preview", "both"]:
            self._preview_code(result.code, language)

        if action in ["save", "both"]:
            self._save_code(result.code, language, root_name)
        elif action == "preview":
            # Ask if they want to save after preview
            if Confirm.ask("\nSave the generated code to file?", default=True):
                self._save_code(result.code, language, root_name)

        elif action == "regenerate":
            self._interactive_generation()  # Start over

    def _preview_code(self, code: str, language: str):
        """Preview generated code with syntax highlighting."""
        self.console.print(
            f"\n[green]📄 Generated {language.title()} Code Preview[/green]"
        )

        try:
            # Map language names for syntax highlighting
            syntax_lang = language.lower()
            if syntax_lang == "golang":
                syntax_lang = "go"

            syntax = Syntax(
                code, syntax_lang, theme="monokai", line_numbers=False, padding=1
            )
            self.console.print()
            self.console.print(syntax)
            self.console.print()

        except Exception:
            # Fallback to plain text if syntax highlighting fails
            self.console.print("[dim]" + code + "[/dim]")

    def _save_code(self, code: str, language: str, root_name: str):
        """Save generated code to file."""
        try:
            # Get language info for file extension
            lang_info = get_language_info(language)
            extension = lang_info["file_extension"]

            # Suggest filename
            default_filename = f"{root_name.lower()}{extension}"
            filename = Prompt.ask("Save as", default=default_filename)

            # Ensure proper extension
            if not filename.endswith(extension):
                filename += extension

            # Save file
            output_path = Path(filename)

            # Check if file exists
            if output_path.exists():
                if not Confirm.ask(
                    f"File {output_path} exists. Overwrite?", default=False
                ):
                    filename = Prompt.ask("Enter new filename")
                    output_path = Path(filename)

            output_path.write_text(code, encoding="utf-8")
            self.console.print(
                f"[green]✅ Code saved to:[/green] [cyan]{output_path}[/cyan]"
            )

        except Exception as e:
            self.console.print(f"[red]⚠ Error saving file:[/red] {e}")

    def _display_warnings(self, warnings: list):
        """Display generation warnings."""
        self.console.print("\n[yellow]⚠️ Warnings:[/yellow]")
        for warning in warnings:
            self.console.print(f"  [yellow]•[/yellow] {warning}")

    def _display_metadata(self, metadata: Dict[str, Any]):
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

    def _show_languages_menu(self):
        """Show detailed languages information menu."""
        while True:
            choice = Prompt.ask(
                "\n[bold]Language Information[/bold]",
                choices=["list", "details", "specific", "back"],
                default="list",
            )

            if choice == "back":
                break
            elif choice == "list":
                self._show_language_list()
            elif choice == "details":
                self._show_detailed_language_info()
            elif choice == "specific":
                self._show_specific_language_info()

    def _show_language_list(self):
        """Show simple language list."""
        languages = list_supported_languages()

        self.console.print("\n[bold]📋 Supported Languages:[/bold]")
        for lang in languages:
            self.console.print(f"  [green]•[/green] {lang}")

    def _show_detailed_language_info(self):
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
            table.add_column("Module", style="dim")

            for lang_name, info in sorted(language_info.items()):
                aliases = (
                    ", ".join(info["aliases"]) if info["aliases"] else "[dim]none[/dim]"
                )

                table.add_row(
                    f"🔧 {lang_name}",
                    info["file_extension"],
                    info["class"],
                    aliases,
                    info["module"],
                )

            self.console.print()
            self.console.print(table)

            # Show usage examples
            self._show_language_usage_examples()

        except Exception as e:
            self.console.print(f"[red]Error loading language info: {e}[/red]")

    def _show_language_usage_examples(self):
        """Show usage examples for languages."""
        examples_panel = Panel(
            """[bold]💡 Language Features Overview:[/bold]

[bold]Currently Available:[/bold]
• Go - Structs with JSON tags, configurable types and pointers
• Python - Dataclasses, Pydantic, and Typeddict models

[bold]Coming Soon:[/bold]
• TypeScript - Interfaces and types
• Rust - Structs with Serde
• Java - POJOs with annotations

[bold]Features:[/bold]
• Smart type detection and conflict resolution
• Configurable naming conventions
• Optional field handling
• Template-based configuration
• Extensible architecture""",
            title="🎯 Language Support",
            border_style="green",
        )
        self.console.print()
        self.console.print(examples_panel)

    def _show_specific_language_info(self):
        """Show information about a specific language."""
        languages = list_supported_languages()

        if not languages:
            self.console.print("[red]No languages available[/red]")
            return

        language = Prompt.ask(
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

    def _display_specific_language_info(self, language: str, info: Dict[str, Any]):
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

    def _show_general_info(self):
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
• Python - Coming soon 🚧
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

    def _show_templates_menu(self):
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

    def _get_language_handler(
        self, language: str
    ) -> Optional[LanguageInteractiveHandler]:
        """Get language-specific interactive handler."""
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
                return handler

        except ImportError:
            pass  # No language-specific handler available
        except Exception as e:
            # Log error but don't fail
            pass

        return None
