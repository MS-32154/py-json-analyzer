"""
Template engine for code generation.

Thin wrapper around Jinja2 with code-generation-specific filters
and utilities.
"""

from pathlib import Path
from typing import Any

import jinja2
from jinja2 import Environment

from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


class TemplateError(Exception):
    """Raised when template operations fail."""

    pass


# ============================================================================
# Template Engine
# ============================================================================


def create_template_env(
    template_dir: Path | None = None,
    trim_blocks: bool = False,
    lstrip_blocks: bool = True,
) -> "Environment":
    """
    Create Jinja2 environment for code generation.

    Args:
        template_dir: Directory containing template files
        trim_blocks: Remove first newline after block
        lstrip_blocks: Strip leading spaces before blocks

    Returns:
        Configured Jinja2 environment

    Raises:
        TemplateError: If template_dir invalid
    """

    # Setup loader
    if template_dir and template_dir.exists():
        loader = jinja2.FileSystemLoader(str(template_dir))
        logger.debug(f"Template environment created with directory: {template_dir}")
    else:
        loader = jinja2.DictLoader({})
        logger.warning(
            "Template environment created without directory (in-memory only)"
        )

    # Create environment
    env = jinja2.Environment(
        loader=loader,
        trim_blocks=trim_blocks,
        lstrip_blocks=lstrip_blocks,
        autoescape=False,  # No HTML escaping for code generation
        keep_trailing_newline=True,  # Preserve final newlines
    )

    # Add custom filters
    env.filters["snake_case"] = _to_snake_case_filter
    env.filters["camel_case"] = _to_camel_case_filter
    env.filters["pascal_case"] = _to_pascal_case_filter
    env.filters["indent"] = _indent_filter
    env.filters["comment"] = _comment_filter

    logger.info(f"Template environment configured with {len(env.filters)} filters")
    return env


def render_template(
    env: "Environment",
    template_name: str,
    context: dict[str, Any],
) -> str:
    """
    Render a template with context.

    Args:
        env: Jinja2 environment
        template_name: Name of template file (e.g., 'struct.go.j2')
        context: Variables to pass to template

    Returns:
        Rendered template content

    Raises:
        TemplateError: If template cannot be rendered
    """
    try:
        template = env.get_template(template_name)
        result = template.render(**context)
        logger.debug(f"Rendered template: {template_name} ({len(result)} chars)")
        return result
    except jinja2.TemplateNotFound as e:
        raise TemplateError(f"Template not found: {template_name}") from e
    except jinja2.TemplateSyntaxError as e:
        raise TemplateError(f"Syntax error in {template_name}: {e}") from e
    except Exception as e:
        raise TemplateError(f"Failed to render {template_name}: {e}") from e


def render_string(
    env: "Environment",
    template_string: str,
    context: dict[str, Any],
) -> str:
    """
    Render a template string with context.

    Args:
        env: Jinja2 environment
        template_string: Template content as string
        context: Variables to pass to template

    Returns:
        Rendered content

    Raises:
        TemplateError: If template cannot be rendered
    """
    try:
        template = env.from_string(template_string)
        result = template.render(**context)
        logger.debug(f"Rendered string template ({len(result)} chars)")
        return result
    except Exception as e:
        raise TemplateError(f"Failed to render string template: {e}") from e


def template_exists(env: "Environment", template_name: str) -> bool:
    """
    Check if a template exists in the environment.

    Args:
        env: Jinja2 environment
        template_name: Name of template to check

    Returns:
        True if template exists, False otherwise
    """
    try:
        env.get_template(template_name)
        return True
    except jinja2.TemplateNotFound:
        return False


def list_templates(env: "Environment") -> list[str]:
    """
    List all available templates.

    Args:
        env: Jinja2 environment

    Returns:
        List of template names
    """
    try:
        templates = env.list_templates()
        logger.debug(f"Found {len(templates)} templates")
        return list(templates)
    except Exception as e:
        logger.warning(f"Failed to list templates: {e}")
        return []


# ============================================================================
# Custom Jinja2 Filters
# ============================================================================


def _to_snake_case_filter(value: str) -> str:
    """Convert value to snake_case."""
    import re

    name = value.replace("-", "_")
    name = re.sub(r"([a-z0-9])([A-Z])", r"\1_\2", name)
    name = name.lower()
    name = re.sub(r"_+", "_", name)
    return name.strip("_")


def _to_camel_case_filter(value: str) -> str:
    """Convert value to camelCase."""
    snake = _to_snake_case_filter(value)
    parts = snake.split("_")
    if not parts:
        return value
    return parts[0].lower() + "".join(p.capitalize() for p in parts[1:])


def _to_pascal_case_filter(value: str) -> str:
    """Convert value to PascalCase."""
    snake = _to_snake_case_filter(value)
    parts = snake.split("_")
    return "".join(p.capitalize() for p in parts if p)


def _indent_filter(value: str, spaces: int = 4) -> str:
    """
    Indent all non-empty lines in a string.

    Args:
        value: String to indent
        spaces: Number of spaces per indent level

    Returns:
        Indented string
    """
    indent = " " * spaces
    lines = str(value).split("\n")
    return "\n".join(indent + line if line.strip() else line for line in lines)


def _comment_filter(value: str, style: str = "//") -> str:
    """
    Add comment markers to each line.

    Args:
        value: String to comment
        style: Comment style ("//", "#", "/*", etc.)

    Returns:
        Commented string
    """
    lines = str(value).split("\n")
    return "\n".join(f"{style} {line}" if line.strip() else line for line in lines)


# ============================================================================
# High-Level Template Manager
# ============================================================================


class TemplateManager:
    """
    Manages templates for a specific generator.

    This is a simple wrapper that holds the Jinja2 environment
    and provides convenient methods.
    """

    __slots__ = ("_env", "_template_dir")

    def __init__(self, template_dir: Path | None = None):
        """
        Initialize template manager.

        Args:
            template_dir: Directory containing templates
        """
        self._template_dir = template_dir
        self._env = create_template_env(template_dir)
        logger.info(f"TemplateManager initialized for: {template_dir}")

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template by name."""
        return render_template(self._env, template_name, context)

    def render_string(self, template_string: str, context: dict[str, Any]) -> str:
        """Render a template string."""
        return render_string(self._env, template_string, context)

    def exists(self, template_name: str) -> bool:
        """Check if template exists."""
        return template_exists(self._env, template_name)

    def list(self) -> list[str]:
        """List available templates."""
        return list_templates(self._env)

    @property
    def template_dir(self) -> Path | None:
        """Get template directory."""
        return self._template_dir
