"""Python code generator: dataclasses, Pydantic v2 models, TypedDict."""

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, override

from ...core.config import GeneratorConfig, build_language_config
from ...core.generator import CodeGenerator
from ...core.naming import NamePlan, plan_names
from ...core.schema import Field, FieldType, Schema
from .config import PYTHON_IMPORTS, STYLE_IMPORTS, PythonConfig, PythonStyle
from .naming import is_plain_key, python_class_name, python_field_name

TEMPLATES = {
    PythonStyle.DATACLASS: "dataclass_file.py.j2",
    PythonStyle.PYDANTIC: "pydantic_file.py.j2",
    PythonStyle.TYPEDDICT: "typeddict_file.py.j2",
}


@dataclass(slots=True)
class _Run:
    """State of one generate() call."""

    names: NamePlan
    # Names used in annotations that need an import (keys of PYTHON_IMPORTS)
    uses: set[str] = field(default_factory=set)


class PythonGenerator(CodeGenerator):
    """Generates dataclasses, Pydantic v2 models or TypedDicts."""

    language_name = "python"
    file_extension = ".py"
    template_dir = Path(__file__).parent / "templates"

    __slots__ = ("python_config",)

    def __init__(self, config: GeneratorConfig):
        super().__init__(config)
        self.python_config = build_language_config(
            PythonConfig, config.language_config, "python"
        )

    @property
    def style(self) -> PythonStyle:
        return self.python_config.style

    @override
    def generate(self, schemas: dict[str, Schema], root_schema_name: str) -> str:
        run = _Run(
            names=plan_names(
                schemas.values(),
                type_identifier=python_class_name,
                field_identifier=self._field_identifier,
                field_separator="_",
            )
        )
        classes = [self._class(s, run) for s in self.dependency_order(schemas)]
        return self.render_template(
            TEMPLATES[self.style],
            {"imports": self._imports(run), "classes": classes},
        )

    def _imports(self, run: _Run) -> list[str]:
        imports = set(STYLE_IMPORTS[self.style])
        by_module: dict[str, list[str]] = {}
        for name in sorted(run.uses):
            by_module.setdefault(PYTHON_IMPORTS[name], []).append(name)
        imports.update(
            f"from {module} import {', '.join(names)}"
            for module, names in by_module.items()
        )
        # Standard library before third party
        return sorted(
            imports,
            key=lambda s: (not s.startswith(("from typing", "from datetime")), s),
        )

    def _field_identifier(self, key: str) -> str:
        match self.style:
            case PythonStyle.TYPEDDICT:
                return key  # a TypedDict describes the dict as-is
            case PythonStyle.PYDANTIC:
                return python_field_name(key, pydantic=True)
            case _:
                return python_field_name(key)

    def _class(self, schema: Schema, run: _Run) -> dict[str, Any]:
        fields = [self._field(f, run) for f in schema.fields]
        cfg = self.python_config
        data: dict[str, Any] = {
            "class_name": run.names.type_name(schema),
            "description": schema.description if self.config.add_comments else None,
            "fields": fields,
        }
        match self.style:
            case PythonStyle.DATACLASS:
                # Positional fields with a default must follow those without
                # one (TypeError otherwise). Stable: JSON order kept per group.
                if not cfg.dataclass_kw_only:
                    fields.sort(key=lambda f: bool(f.get("use_default")))
                data |= {
                    "frozen": cfg.dataclass_frozen,
                    "slots": cfg.dataclass_slots,
                    "kw_only": cfg.dataclass_kw_only,
                }
            case PythonStyle.PYDANTIC:
                data |= {
                    "config_dict": cfg.pydantic_config_dict,
                    "extra_forbid": cfg.pydantic_extra_forbid,
                }
            case PythonStyle.TYPEDDICT:
                # Keys that aren't identifiers need TypedDict("Name", {...})
                data["functional"] = not all(
                    is_plain_key(f.original_name) for f in schema.fields
                )
        return data

    def _field(self, fld: Field, run: _Run) -> dict[str, Any]:
        name = run.names.field_name(fld)
        data: dict[str, Any] = {
            "name": name,
            "type": self._type(fld, run),
            "key": py_str(fld.original_name),
        }
        # Pydantic carries the note in Field(description=...) instead
        if (
            self.config.add_comments
            and fld.description
            and self.style != PythonStyle.PYDANTIC
        ):
            data["comment"] = fld.description
        match self.style:
            case PythonStyle.DATACLASS if fld.optional:
                data["use_default"] = True
                data["default_value"] = "None"
            case PythonStyle.PYDANTIC:
                args = []
                if fld.original_name != name:  # the alias maps it to the JSON key
                    args.append(f"alias={py_str(fld.original_name)}")
                if fld.description and self.config.add_comments:
                    args.append(f"description={py_str(fld.description)}")
                if fld.optional:
                    args.append("default=None")
                if args:
                    data["assignment"] = field_call(
                        f"    {name}: {data['type']} = ", args
                    )
        return data

    def _type(self, fld: Field, run: _Run) -> str:
        match fld.type:
            case FieldType.ARRAY:
                annotation = self._element_type(fld, run)
                for _ in range(fld.array_dimensions):
                    annotation = f"list[{annotation}]"
            case FieldType.OBJECT if fld.nested_schema is not None:
                annotation = run.names.type_name(fld.nested_schema)
            case FieldType.OBJECT:
                annotation = self._primitive(FieldType.UNKNOWN, run)
            case _:
                annotation = self._primitive(fld.type, run)
        if not fld.optional:
            return annotation
        if self.style == PythonStyle.TYPEDDICT:
            run.uses.add("NotRequired")
        return self.python_config.optional(annotation)

    def _element_type(self, fld: Field, run: _Run) -> str:
        if fld.array_element_schema:
            return run.names.type_name(fld.array_element_schema)
        return self._primitive(fld.array_element_type or FieldType.UNKNOWN, run)

    def _primitive(self, field_type: FieldType, run: _Run) -> str:
        annotation = self.python_config.type_map.get(field_type, "Any")
        if annotation in PYTHON_IMPORTS:
            run.uses.add(annotation)
        return annotation


def py_str(text: str) -> str:
    """Python string literal, quoted the way ruff/black format it.

    Double quotes unless the text contains a double quote and no single one.
    """
    literal = repr(text)
    if literal.startswith("'") and '"' not in text:
        literal = '"' + literal[1:-1].replace("\\'", "'") + '"'
    return literal


LINE_LENGTH = 88


def field_call(prefix: str, args: list[str]) -> str:
    """`` = Field(...)`` wrapped the way ruff/black format it.

    One line if it fits; otherwise the arguments on one indented line; if that
    is still too long, one argument per line with a trailing comma.
    """
    one_line = f"Field({', '.join(args)})"
    if len(prefix) + len(one_line) <= LINE_LENGTH:
        return one_line
    hugged = "        " + ", ".join(args)
    if len(hugged) <= LINE_LENGTH:
        return f"Field(\n{hugged}\n    )"
    lines = "".join(f"        {arg},\n" for arg in args)
    return f"Field(\n{lines}    )"
