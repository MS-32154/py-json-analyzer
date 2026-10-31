"""Go code generator: structs with JSON tags."""

from .config import GoConfig
from .generator import GoGenerator
from .interactive import GoInteractiveHandler
from .naming import go_identifier, go_json_tag

__all__ = [
    "GoConfig",
    "GoGenerator",
    "GoInteractiveHandler",
    "go_identifier",
    "go_json_tag",
]
