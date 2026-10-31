"""Rust-specific configuration."""

from dataclasses import dataclass


@dataclass(slots=True, kw_only=True)
class RustConfig:
    """Rust-specific options.

    Attributes:
        deny_unknown_fields: Add ``#[serde(deny_unknown_fields)]`` so
            deserializing fails on keys the struct doesn't have.
    """

    deny_unknown_fields: bool = False

    def to_dict(self) -> dict:
        return {"deny_unknown_fields": self.deny_unknown_fields}
