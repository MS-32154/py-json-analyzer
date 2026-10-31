"""TypeScript code generator: interfaces or Zod schemas."""

from .config import TypeScriptConfig, TypeScriptStyle
from .generator import TypeScriptGenerator
from .naming import property_key, ts_type_name
from .plugin import PLUGIN

__all__ = [
    "PLUGIN",
    "TypeScriptConfig",
    "TypeScriptGenerator",
    "TypeScriptStyle",
    "property_key",
    "ts_type_name",
]
