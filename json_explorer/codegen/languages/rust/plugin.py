"""Rust language plugin."""

from ...core.plugin import CliOption, LanguagePlugin
from .generator import RustGenerator

PLUGIN = LanguagePlugin(
    name="rust",
    display_name="Rust",
    generator=RustGenerator,
    aliases=("rs",),
    cli_options=(
        CliOption(
            "--rust-deny-unknown",
            "deny_unknown_fields",
            "Add #[serde(deny_unknown_fields)] to Rust structs",
        ),
    ),
    examples=(
        ("Structs with serde derives", "--generate rust"),
        ("Reject unknown keys", "--generate rust --rust-deny-unknown"),
        ("Write to a file", "--generate rs --output models.rs"),
    ),
)
