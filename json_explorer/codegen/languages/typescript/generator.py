"""TypeScript code generator: interfaces, or Zod schemas with inferred types.

Keys stay exactly as in the JSON (quoted when they aren't identifiers). A key
that can be missing is ``key?: T`` / ``.optional()``; a value that can be
null is ``T | null`` / ``.nullable()``. Mixed values become unions.
JSON.parse leaves date/time strings as strings, so interfaces type them as
``string`` (with a doc comment); Zod validates the standard formats.
"""

from pathlib import Path
from typing import override

from ...core.config import GeneratorConfig, build_language_config
from ...core.generator import CodeGenerator
from ...core.naming import NamePlan, plan_names
from ...core.schema import Field, FieldType, Schema
from .config import TypeScriptConfig, TypeScriptStyle
from .naming import property_key, ts_type_name

_TS_TYPES = {
    FieldType.STRING: "string",
    FieldType.INTEGER: "number",
    FieldType.FLOAT: "number",
    FieldType.BOOLEAN: "boolean",
    FieldType.DATE_TIME: "string",
    FieldType.LOCAL_DATE_TIME: "string",
    FieldType.DATE: "string",
    FieldType.TIME: "string",
    FieldType.DURATION: "string",
    FieldType.OBJECT: "Record<string, unknown>",
    FieldType.ARRAY: "unknown[]",
    FieldType.UNKNOWN: "unknown",
}
_FORMAT_NOTES = {
    FieldType.DATE_TIME: "RFC 3339 date-time",
    FieldType.LOCAL_DATE_TIME: "Date-time without a UTC offset",
    FieldType.DATE: "Date (YYYY-MM-DD)",
    FieldType.TIME: "Time of day",
    FieldType.DURATION: "ISO 8601 duration",
}
# Zod 4 validators; z.iso.time() rejects offsets ("10:30:00Z"), which the
# analyzer accepts as times, so times are plain strings.
_ZOD_TYPES = {
    FieldType.STRING: "z.string()",
    FieldType.INTEGER: "z.number().int()",
    FieldType.FLOAT: "z.number()",
    FieldType.BOOLEAN: "z.boolean()",
    FieldType.DATE_TIME: "z.iso.datetime({ offset: true })",
    FieldType.LOCAL_DATE_TIME: "z.iso.datetime({ local: true })",
    FieldType.DATE: "z.iso.date()",
    FieldType.TIME: "z.string()",
    FieldType.DURATION: "z.iso.duration()",
    FieldType.OBJECT: "z.record(z.string(), z.unknown())",
    FieldType.ARRAY: "z.array(z.unknown())",
    FieldType.UNKNOWN: "z.unknown()",
}


class TypeScriptGenerator(CodeGenerator):
    """Generates TypeScript interfaces or Zod schemas."""

    language_name = "typescript"
    file_extension = ".ts"
    template_dir = Path(__file__).parent / "templates"

    __slots__ = ("ts_config",)

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.ts_config = build_language_config(
            TypeScriptConfig, config.language_config, "typescript"
        )

    @override
    def format_code(self, code: str) -> str:
        """Prettier keeps at most one blank line in a row."""
        lines = super().format_code(code).split("\n")
        kept = [line for i, line in enumerate(lines) if line or i == 0 or lines[i - 1]]
        return "\n".join(kept)

    @property
    def zod(self) -> bool:
        return self.ts_config.style == TypeScriptStyle.ZOD

    @override
    def generate(self, schemas: dict[str, Schema], root_schema_name: str) -> str:
        # Property keys are the JSON keys; only type names need planning
        names = plan_names(
            schemas.values(), type_identifier=ts_type_name, field_identifier=str
        )
        declarations = [
            self._zod_object(s, names) if self.zod else self._interface(s, names)
            for s in self.dependency_order(schemas)
        ]
        return self.render_template(
            "file.ts.j2", {"zod": self.zod, "declarations": declarations}
        )

    # -- interfaces ----------------------------------------------------------

    def _interface(self, schema: Schema, names: NamePlan) -> str:
        lines = [f"export interface {names.type_name(schema)} {{"]
        for fld in schema.fields:
            note = fld.description or _FORMAT_NOTES.get(fld.type)
            if note and self.config.add_comments:
                lines.append(f"  /** {note} */")
            mark = "?" if fld.missing else ""
            lines.append(
                f"  {property_key(fld.original_name)}{mark}: {self._ts(fld, names)};"
            )
        if len(lines) == 1:
            return lines[0] + "}"
        return "\n".join([*lines, "}"])

    def _ts(self, fld: Field, names: NamePlan) -> str:
        match fld.type:
            case FieldType.OBJECT if fld.nested_schema is not None:
                annotation = names.type_name(fld.nested_schema)
            case FieldType.ARRAY:
                element = self._ts_element(fld, names)
                annotation = element + "[]" * fld.array_dimensions
            case FieldType.CONFLICT:
                annotation = self._ts_union(fld)
            case _:
                annotation = _TS_TYPES[fld.type]
        return f"{annotation} | null" if fld.nullable else annotation

    def _ts_element(self, fld: Field, names: NamePlan) -> str:
        if fld.array_element_schema is not None:
            element = names.type_name(fld.array_element_schema)
        elif fld.array_element_type == FieldType.CONFLICT:
            element = "unknown"  # the element kinds aren't recorded
        else:
            element = _TS_TYPES[fld.array_element_type or FieldType.UNKNOWN]
        if fld.array_element_nullable and element != "unknown":
            element += " | null"
        return f"({element})" if " " in element else element

    @staticmethod
    def _ts_union(fld: Field) -> str:
        members = dict.fromkeys(_TS_TYPES[t] for t in fld.conflicting_types)
        return " | ".join(members) or "unknown"

    # -- Zod -----------------------------------------------------------------

    def _zod_object(self, schema: Schema, names: NamePlan) -> str:
        name = names.type_name(schema)
        fields = []
        for fld in schema.fields:
            if fld.description and self.config.add_comments:
                fields.append(f"  /** {fld.description} */")
            fields.append(
                f"  {property_key(fld.original_name)}: {self._zod(fld, names)},"
            )
        body = (
            "z.object({})"
            if not fields
            else "z.object({\n" + "\n".join(fields) + "\n})"
        )
        return (
            f"export const {name} = {body};\n"
            f"export type {name} = z.infer<typeof {name}>;"
        )

    def _zod(self, fld: Field, names: NamePlan) -> str:
        match fld.type:
            case FieldType.OBJECT if fld.nested_schema is not None:
                schema = names.type_name(fld.nested_schema)
            case FieldType.ARRAY:
                schema = self._zod_element(fld, names)
                for _ in range(fld.array_dimensions):
                    schema = f"z.array({schema})"
            case FieldType.CONFLICT:
                members = dict.fromkeys(_ZOD_TYPES[t] for t in fld.conflicting_types)
                schema = (
                    f"z.union([{', '.join(members)}])"
                    if len(members) > 1
                    else "z.unknown()"
                )
            case _:
                schema = _ZOD_TYPES[fld.type]
        if fld.nullable:
            schema += ".nullable()"
        if fld.missing:
            schema += ".optional()"
        return schema

    def _zod_element(self, fld: Field, names: NamePlan) -> str:
        if fld.array_element_schema is not None:
            element = names.type_name(fld.array_element_schema)
        elif fld.array_element_type in (None, FieldType.CONFLICT, FieldType.UNKNOWN):
            return "z.unknown()"
        else:
            element = _ZOD_TYPES[fld.array_element_type]
        return element + ".nullable()" if fld.array_element_nullable else element
