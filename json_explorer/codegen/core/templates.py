"""
Template engine wrapper for code generation.

Provides a clean, language-agnostic interface for Jinja2 template rendering
with common utilities for code generation.
"""

from typing import Dict, Any, Optional
from pathlib import Path
from .naming import NameSanitizer

try:
    from jinja2 import (
        Environment,
        FileSystemLoader,
        DictLoader,
        select_autoescape,
    )
except ImportError:
    # Fallback for environments without jinja2
    Environment = None
    FileSystemLoader = None
    BaseLoader = None
    DictLoader = None
    select_autoescape = None


class TemplateError(Exception):
    """Exception raised for template-related errors."""

    pass


class TemplateEngine:
    """Language-agnostic wrapper for Jinja2 template engine."""

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize template engine.

        Args:
            template_dir: Directory containing template files
        """
        self._name_sanitizer = NameSanitizer()

        if Environment is None:
            raise TemplateError(
                "Jinja2 is required for template functionality. "
                "Install with: pip install jinja2"
            )

        self.template_dir = template_dir
        self._env = None
        self._setup_environment()

    def _setup_environment(self):
        """Setup Jinja2 environment with code generation utilities."""
        if self.template_dir and self.template_dir.exists():
            loader = FileSystemLoader(str(self.template_dir))
        else:
            # Use in-memory templates as fallback
            loader = DictLoader({})

        self._env = Environment(
            loader=loader,
            autoescape=select_autoescape(["html", "xml"]),
            lstrip_blocks=True,
            # trim_blocks=True,
        )

        # Add language-agnostic filters for code generation
        self._env.filters["snake_case"] = self._snake_case_filter
        self._env.filters["camel_case"] = self._camel_case_filter
        self._env.filters["pascal_case"] = self._pascal_case_filter
        self._env.filters["indent"] = self._indent_filter
        self._env.filters["comment"] = self._comment_filter

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of template file (e.g., 'struct.go.j2')
            context: Variables to pass to template

        Returns:
            Rendered template content
        """
        try:
            template = self._env.get_template(template_name)
            return template.render(**context)
        except Exception as e:
            raise TemplateError(f"Failed to render template {template_name}: {str(e)}")

    def render_string(self, template_string: str, context: Dict[str, Any]) -> str:
        """
        Render a template string with the given context.

        Args:
            template_string: Template content as string
            context: Variables to pass to template

        Returns:
            Rendered content
        """
        try:
            template = self._env.from_string(template_string)
            return template.render(**context)
        except Exception as e:
            raise TemplateError(f"Failed to render template string: {str(e)}")

    def add_template(self, name: str, content: str):
        """
        Add an in-memory template.

        Args:
            name: Template name
            content: Template content
        """
        if not isinstance(self._env.loader, DictLoader):
            # Convert to DictLoader to support in-memory templates
            self._env.loader = DictLoader({})

        self._env.loader.mapping[name] = content

    def template_exists(self, template_name: str) -> bool:
        """Check if a template exists."""
        try:
            self._env.get_template(template_name)
            return True
        except:
            return False

    def list_templates(self) -> list[str]:
        """List all available templates."""
        try:
            return self._env.list_templates()
        except:
            return []

    # Language-agnostic template filters

    def _snake_case_filter(self, value: str) -> str:
        return self._name_sanitizer._to_snake_case(value)

    def _camel_case_filter(self, value: str) -> str:
        return self._name_sanitizer._to_camel_case(value)

    def _pascal_case_filter(self, value: str) -> str:
        return self._name_sanitizer._to_pascal_case(value)

    def _indent_filter(self, value: str, spaces: int = 4) -> str:
        """Indent all lines in a string."""
        indent = " " * spaces
        lines = str(value).split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)

    def _comment_filter(self, value: str, style: str = "//") -> str:
        """Add comment markers to each line."""
        lines = str(value).split("\n")
        return "\n".join(f"{style} {line}" if line.strip() else line for line in lines)


def create_template_engine(template_dir: Optional[Path] = None) -> TemplateEngine:
    """
    Create a template engine instance.

    Args:
        template_dir: Directory containing template files

    Returns:
        Configured TemplateEngine instance
    """
    return TemplateEngine(template_dir)
