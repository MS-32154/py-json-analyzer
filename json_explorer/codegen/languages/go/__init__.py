"""Go code generator: structs with JSON tags."""

from .config import GoConfig
from .generator import GoGenerator
from .interactive import GoInteractiveHandler
from .naming import go_identifier, go_json_tag
from .plugin import PLUGIN

__all__ = [
    "PLUGIN",
    "GoConfig",
    "GoGenerator",
    "GoInteractiveHandler",
    "go_identifier",
    "go_json_tag",
]
