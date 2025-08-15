"""
Template engine wrapper for code generation.

Provides a simple interface for Jinja2 template rendering
with common utilities for code generation.
"""

import os
from typing import Dict, Any, Optional
from pathlib import Path

try:
    from jinja2 import (
        Environment,
        FileSystemLoader,
        BaseLoader,
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
    """Wrapper for Jinja2 template engine with code generation utilities."""

    def __init__(self, template_dir: Optional[Path] = None):
        """
        Initialize template engine.

        Args:
            template_dir: Directory containing template files
        """
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
            # Use in-memory templates
            loader = DictLoader({})

        self._env = Environment(
            loader=loader,
            autoescape=select_autoescape(["html", "xml"]),
            # trim_blocks=True,
            lstrip_blocks=True,
        )

        # Add custom filters for code generation
        self._env.filters["snake_case"] = self._snake_case_filter
        self._env.filters["camel_case"] = self._camel_case_filter
        self._env.filters["pascal_case"] = self._pascal_case_filter
        self._env.filters["indent"] = self._indent_filter
        self._env.filters["comment"] = self._comment_filter

    def render_template(self, template_name: str, context: Dict[str, Any]) -> str:
        """
        Render a template with the given context.

        Args:
            template_name: Name of template file
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

    # Template filters for code generation

    def _snake_case_filter(self, value: str) -> str:
        """Convert string to snake_case."""
        import re

        # Insert underscore before uppercase letters
        s1 = re.sub("([a-z0-9])([A-Z])", r"\1_\2", str(value))
        # Replace spaces and hyphens with underscores
        s2 = re.sub(r"[-\s]+", "_", s1)
        return s2.lower()

    def _camel_case_filter(self, value: str) -> str:
        """Convert string to camelCase."""
        snake = self._snake_case_filter(value)
        parts = snake.split("_")
        if not parts:
            return str(value)
        return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])

    def _pascal_case_filter(self, value: str) -> str:
        """Convert string to PascalCase."""
        snake = self._snake_case_filter(value)
        parts = snake.split("_")
        return "".join(p.capitalize() for p in parts if p)

    def _indent_filter(self, value: str, spaces: int = 4) -> str:
        """Indent all lines in a string."""
        indent = " " * spaces
        lines = str(value).split("\n")
        return "\n".join(indent + line if line.strip() else line for line in lines)

    def _comment_filter(self, value: str, style: str = "//") -> str:
        """Add comment markers to each line."""
        lines = str(value).split("\n")
        return "\n".join(f"{style} {line}" if line.strip() else line for line in lines)


# Built-in templates for common patterns
GO_STRUCT_TEMPLATE = """
{%- if description %}
// {{ description }}
{%- endif %}
type {{ struct_name }} struct {
{%- for field in fields %}
    {%- if field.comment %}
    // {{ field.comment }}
    {%- endif %}
    {{ field.name }} {{ field.type }} {% if field.json_tag %} {{ field.json_tag }} {% endif %}
{%- endfor %}
}
"""

PYTHON_DATACLASS_TEMPLATE = """
@dataclass
class {{ class_name }}:
{%- for field in fields %}
    {{ field.name }}: {{ field.type }}{% if field.optional %} = None{% endif %}
{%- endfor %}
"""

# Default template engine instance
_default_engine = None


def get_default_template_engine() -> TemplateEngine:
    """Get the default template engine instance."""
    global _default_engine
    if _default_engine is None:
        _default_engine = TemplateEngine()

        # Add built-in templates
        _default_engine.add_template("go_struct", GO_STRUCT_TEMPLATE)
        _default_engine.add_template("python_dataclass", PYTHON_DATACLASS_TEMPLATE)

    return _default_engine


def render_go_struct(
    struct_name: str, fields: list, context: Dict[str, Any] = None
) -> str:
    """
    Convenience function to render a Go struct.

    Args:
        struct_name: Name of the struct
        fields: List of field dictionaries
        context: Additional context variables

    Returns:
        Rendered Go struct code
    """
    engine = get_default_template_engine()
    template_context = {"struct_name": struct_name, "fields": fields, **(context or {})}

    return engine.render_template("go_struct", template_context)
