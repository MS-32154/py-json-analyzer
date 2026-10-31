"""Go code generator: structs with JSON tags."""

import json
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, override

from ...core.config import GeneratorConfig, build_language_config
from ...core.generator import CodeGenerator
from ...core.naming import NamePlan, plan_names
from ...core.schema import Field, FieldType, Schema
from .config import UNKNOWN_TYPE, GoConfig
from .naming import go_identifier, go_json_tag, is_valid_json_tag_name


@dataclass(slots=True)
class _Run:
    """State of one generate() call."""

    names: NamePlan
    imports: set[str] = field(default_factory=set)


class GoGenerator(CodeGenerator):
    """Generates Go structs with JSON tags."""

    language_name = "go"
    file_extension = ".go"
    template_dir = Path(__file__).parent / "templates"

    __slots__ = ("go_config",)

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.go_config = build_language_config(GoConfig, config.language_config, "go")

    @override
    def generate(self, schemas: dict[str, Schema], root_schema_name: str) -> str:
        run = _Run(
            names=plan_names(
                schemas.values(),
                type_identifier=lambda name: go_identifier(name, fallback="Type"),
                field_identifier=go_identifier,
            )
        )
        structs = [self._struct(s, run) for s in self.dependency_order(schemas)]
        return self.render_template(
            "complete_file.go.j2",
            {
                "package_name": self.config.package_name,
                "imports": sorted(run.imports),
                "structs": structs,
            },
        )

    @override
    def format_code(self, code: str) -> str:
        """gofmt keeps at most one blank line in a row."""
        lines = super().format_code(code).split("\n")
        kept = [line for i, line in enumerate(lines) if line or i == 0 or lines[i - 1]]
        return "\n".join(kept)

    def _struct(self, schema: Schema, run: _Run) -> dict[str, Any]:
        fields = [self._field(f, run) for f in schema.fields]
        _align_like_gofmt(fields)
        return {
            "struct_name": run.names.type_name(schema),
            "description": schema.description if self.config.add_comments else None,
            "fields": fields,
        }

    def _field(self, fld: Field, run: _Run) -> dict[str, Any]:
        # encoding/json can't map keys like `a,b` or `q"k` with a tag: leave
        # the field out (with a note) rather than map it to the wrong key.
        if not is_valid_json_tag_name(fld.original_name):
            key = json.dumps(fld.original_name, ensure_ascii=False)
            return {
                "skipped": f"JSON key {key} can't be expressed as a Go struct tag; "
                "field omitted"
            }
        data = {
            "name": run.names.field_name(fld),
            "type": self._type(fld, run),
            "json_tag": go_json_tag(
                fld.original_name,
                omitempty=fld.optional and self.config.json_tag_omitempty,
            ),
        }
        if self.config.add_comments and fld.description:
            data["comment"] = fld.description
        return data

    def _type(self, fld: Field, run: _Run) -> str:
        match fld.type:
            case FieldType.ARRAY:
                return "[]" * fld.array_dimensions + self._element_type(fld, run)
            case FieldType.OBJECT:
                if fld.nested_schema is None:
                    return UNKNOWN_TYPE
                name = run.names.type_name(fld.nested_schema)
                pointer = fld.optional and self.go_config.use_pointers_for_optional
                return f"*{name}" if pointer else name
            case _:
                self._note_import(fld.type, run)
                return self.go_config.get_go_type(fld.type, is_optional=fld.optional)

    def _element_type(self, fld: Field, run: _Run) -> str:
        if fld.array_element_schema:
            element = run.names.type_name(fld.array_element_schema)
        elif fld.array_element_type in (None, FieldType.UNKNOWN):
            return UNKNOWN_TYPE
        else:
            self._note_import(fld.array_element_type, run)
            element = self.go_config.type_map.get(fld.array_element_type, UNKNOWN_TYPE)
        # *T keeps null elements apart from zero values (any already holds nil)
        if fld.array_element_nullable and element != UNKNOWN_TYPE:
            return f"*{element}"
        return element

    def _note_import(self, field_type: FieldType, run: _Run) -> None:
        if (
            field_type == FieldType.DATE_TIME
            and self.go_config.time_type == "time.Time"
        ):
            run.imports.add('"time"')


def _align_like_gofmt(fields: list[dict[str, Any]]) -> None:
    """Pad names and types into columns the way gofmt does.

    gofmt aligns consecutive field lines; a comment line starts a new group.
    Sets ``name_col`` and ``type_col`` (padded) on every field.
    """
    groups: list[list[dict[str, Any]]] = [[]]
    for fld in fields:
        if "skipped" in fld or fld.get("comment"):
            groups.append([])
        if "skipped" not in fld:
            groups[-1].append(fld)
    for group in groups:
        if not group:
            continue
        name_width = max(len(f["name"]) for f in group)
        type_width = max(len(f["type"]) for f in group)
        for fld in group:
            fld["name_col"] = fld["name"].ljust(name_width)
            fld["type_col"] = fld["type"].ljust(type_width)
