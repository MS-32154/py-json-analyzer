"""Jinja2 template rendering for code generators."""

from pathlib import Path
from typing import Any

import jinja2

from json_explorer.errors import JsonExplorerError
from json_explorer.logging_config import get_logger

logger = get_logger(__name__)


class TemplateError(JsonExplorerError):
    """Raised when a template can't be found or rendered."""


class TemplateManager:
    """Renders a generator's templates from its template directory."""

    __slots__ = ("_env", "_template_dir")

    def __init__(self, template_dir: Path):
        self._template_dir = template_dir
        self._env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(str(template_dir)),
            lstrip_blocks=True,
            autoescape=False,  # generating source code, not HTML
            keep_trailing_newline=True,
        )
        logger.debug("TemplateManager initialized for: %s", template_dir)

    @property
    def template_dir(self) -> Path:
        return self._template_dir

    def render(self, template_name: str, context: dict[str, Any]) -> str:
        """Render a template file with the given context."""
        try:
            return self._env.get_template(template_name).render(**context)
        except jinja2.TemplateNotFound as e:
            raise TemplateError(f"Template not found: {template_name}") from e
        except jinja2.TemplateError as e:
            raise TemplateError(f"Failed to render {template_name}: {e}") from e
