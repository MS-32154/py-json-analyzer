"""Rust code generator: structs with serde derives."""

from .config import RustConfig
from .generator import RustGenerator
from .naming import rust_field_name, rust_string, rust_type_name
from .plugin import PLUGIN

__all__ = [
    "PLUGIN",
    "RustConfig",
    "RustGenerator",
    "rust_field_name",
    "rust_string",
    "rust_type_name",
]
