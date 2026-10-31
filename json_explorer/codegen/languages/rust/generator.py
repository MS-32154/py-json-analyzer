"""Rust code generator: structs with serde derives.

Fields are snake_case with ``#[serde(rename = "...")]`` where the JSON key
differs. A key that can be missing or a value that can be null is
``Option<T>``; keys that can be missing are also skipped when serializing
None, so serializing reproduces the original shape. Unknown and mixed values
are ``serde_json::Value``. Date/time strings stay ``String`` (documented).
"""

from dataclasses import dataclass, field
from pathlib import Path
from typing import override

from ...core.config import GeneratorConfig, build_language_config
from ...core.generator import CodeGenerator
from ...core.naming import NamePlan, plan_names
from ...core.schema import Field, FieldType, Schema
from .config import RustConfig
from .naming import rust_field_name, rust_string, rust_type_name

VALUE = "Value"  # serde_json::Value, imported when used

_RUST_TYPES = {
    FieldType.STRING: "String",
    FieldType.INTEGER: "i64",
    FieldType.FLOAT: "f64",
    FieldType.BOOLEAN: "bool",
    FieldType.DATE_TIME: "String",
    FieldType.LOCAL_DATE_TIME: "String",
    FieldType.DATE: "String",
    FieldType.TIME: "String",
    FieldType.DURATION: "String",
    FieldType.OBJECT: VALUE,
    FieldType.ARRAY: f"Vec<{VALUE}>",
    FieldType.UNKNOWN: VALUE,
    FieldType.CONFLICT: VALUE,
}
_FORMAT_NOTES = {
    FieldType.DATE_TIME: "RFC 3339 date-time",
    FieldType.LOCAL_DATE_TIME: "Date-time without a UTC offset",
    FieldType.DATE: "Date (YYYY-MM-DD)",
    FieldType.TIME: "Time of day",
    FieldType.DURATION: "ISO 8601 duration",
}


@dataclass(slots=True)
class _Run:
    names: NamePlan
    uses_value: bool = False
    structs: list[str] = field(default_factory=list)


class RustGenerator(CodeGenerator):
    """Generates Rust structs with serde derives."""

    language_name = "rust"
    file_extension = ".rs"
    template_dir = Path(__file__).parent / "templates"

    __slots__ = ("rust_config",)

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.rust_config = build_language_config(
            RustConfig, config.language_config, "rust"
        )

    @override
    def generate(self, schemas: dict[str, Schema], root_schema_name: str) -> str:
        run = _Run(
            names=plan_names(
                schemas.values(),
                type_identifier=rust_type_name,
                field_identifier=rust_field_name,
                field_separator="_",
            )
        )
        structs = [self._struct(s, run) for s in self.dependency_order(schemas)]
        return self.render_template(
            "file.rs.j2", {"uses_value": run.uses_value, "structs": structs}
        )

    @override
    def format_code(self, code: str) -> str:
        """rustfmt keeps at most one blank line in a row."""
        lines = super().format_code(code).split("\n")
        kept = [line for i, line in enumerate(lines) if line or i == 0 or lines[i - 1]]
        return "\n".join(kept)

    def _struct(self, schema: Schema, run: _Run) -> str:
        lines = ["#[derive(Debug, Clone, PartialEq, Serialize, Deserialize)]"]
        if self.rust_config.deny_unknown_fields:
            lines.append("#[serde(deny_unknown_fields)]")
        lines.append(f"pub struct {run.names.type_name(schema)} {{")
        for fld in schema.fields:
            lines.extend(self._field(fld, run))
        if len(lines) and lines[-1].endswith("{"):
            lines[-1] += "}"
            return "\n".join(lines)
        return "\n".join([*lines, "}"])

    def _field(self, fld: Field, run: _Run) -> list[str]:
        lines = []
        note = fld.description or _FORMAT_NOTES.get(fld.type)
        if note and self.config.add_comments:
            lines.append(f"    /// {note}")
        name = run.names.field_name(fld)
        attrs = []
        if name.removeprefix("r#") != fld.original_name:
            attrs.append(f"rename = {rust_string(fld.original_name)}")
        if fld.missing:
            attrs.append('skip_serializing_if = "Option::is_none"')
        if attrs:
            lines.append(f"    #[serde({', '.join(attrs)})]")
        rust_type = self._type(fld, run)
        if fld.optional and rust_type != VALUE:  # Value already holds null
            rust_type = f"Option<{rust_type}>"
        lines.append(f"    pub {name}: {rust_type},")
        return lines

    def _type(self, fld: Field, run: _Run) -> str:
        match fld.type:
            case FieldType.OBJECT if fld.nested_schema is not None:
                return run.names.type_name(fld.nested_schema)
            case FieldType.ARRAY:
                rust_type = self._element(fld, run)
                for _ in range(fld.array_dimensions):
                    rust_type = f"Vec<{rust_type}>"
                return rust_type
            case _:
                rust_type = _RUST_TYPES[fld.type]
                run.uses_value |= VALUE in rust_type
                return rust_type

    def _element(self, fld: Field, run: _Run) -> str:
        if fld.array_element_schema is not None:
            element = run.names.type_name(fld.array_element_schema)
        else:
            element = _RUST_TYPES[fld.array_element_type or FieldType.UNKNOWN]
            if element.startswith("Vec<"):  # the analyzer gives the innermost type
                element = VALUE
        if element == VALUE:
            run.uses_value = True
            return element
        return f"Option<{element}>" if fld.array_element_nullable else element
