"""Compile checks: generated code must be valid for the real toolchain.

The other codegen tests only check that strings appear in the output, which
let broken code through. These tests feed the output to the language itself:

- Python: the module is executed, Pydantic models are rebuilt, and every
  class's annotations are resolved with ``typing.get_type_hints``.
- Go: the file is type-checked with ``go vet`` (skipped when Go is missing).

Cases marked ``xfail`` are known bugs from the code review (numbers refer to
section A of notes/code_review_2026-10-31.md). They are strict: when a fix
makes one pass, the run fails until the mark is removed.
"""

import json
import os
import shutil
import subprocess
import typing
from pathlib import Path

import pytest
from json_explorer.codegen import quick_generate

DATA_SAMPLES = Path(__file__).parent.parent / "data_samples"

CASES: dict[str, typing.Any] = {
    "flat": {"id": 1, "name": "Alice", "active": True, "score": 9.5, "tags": ["a"]},
    "nested": {"name": "x", "address": {"name": "y", "city": "z"}},
    "optional_before_required": [{"a": 1, "b": "x"}, {"b": "y"}],
    "digit_key": {"123abc": 1},
    "quote_key": {'q"k': 1},
} | {p.stem: json.loads(p.read_text()) for p in sorted(DATA_SAMPLES.glob("*.json"))}

TARGETS = ("dataclass", "pydantic", "typeddict", "go")

BUG_1 = "#1 nested type referenced by a suffixed name that doesn't exist"
BUG_2 = "#2 dataclass: required field after optional (default) field"
BUG_6 = "#6 digit-leading key becomes an _underscore name"
BUG_7 = "#7 JSON key not escaped in generated code"

KNOWN_BUGS: dict[tuple[str, str], str] = {
    ("nested", "dataclass"): BUG_1,
    ("nested", "pydantic"): BUG_1,
    ("nested", "typeddict"): BUG_1,
    ("nested", "go"): BUG_1,
    ("optional_before_required", "dataclass"): BUG_2,
    ("digit_key", "pydantic"): BUG_6,
    ("digit_key", "go"): BUG_6,
    ("quote_key", "pydantic"): BUG_7,
    ("quote_key", "go"): BUG_7,
    ("001_sample_project", "dataclass"): f"{BUG_2}; then {BUG_1}",
    ("001_sample_project", "pydantic"): BUG_1,
    ("001_sample_project", "typeddict"): BUG_1,
    ("001_sample_project", "go"): BUG_1,
    ("002_sample_project", "dataclass"): f"{BUG_2}; then {BUG_1}",
    ("002_sample_project", "pydantic"): BUG_1,
    ("002_sample_project", "typeddict"): BUG_1,
    ("002_sample_project", "go"): BUG_1,
}


def _params():
    for case in CASES:
        for target in TARGETS:
            marks = []
            if reason := KNOWN_BUGS.get((case, target)):
                marks.append(pytest.mark.xfail(reason=reason, strict=True))
            yield pytest.param(case, target, marks=marks, id=f"{case}-{target}")


def _find_go() -> str | None:
    return os.environ.get("JSON_EXPLORER_GO") or shutil.which("go")


def check_python(code: str) -> None:
    """Execute generated Python and resolve every class's annotations."""
    namespace: dict[str, typing.Any] = {"__name__": "generated"}
    exec(compile(code, "<generated>", "exec"), namespace)
    classes = [
        obj
        for obj in namespace.values()
        if isinstance(obj, type) and obj.__module__ == "generated"
    ]
    assert classes, "no classes were generated"
    for cls in classes:
        if hasattr(cls, "model_rebuild"):  # Pydantic: resolve forward refs now
            cls.model_rebuild()
        typing.get_type_hints(cls)


def check_go(code: str, workdir: Path) -> None:
    """Type-check generated Go with `go vet` in a throwaway module."""
    go = _find_go()
    if go is None:
        pytest.skip("Go toolchain not found (set JSON_EXPLORER_GO or add go to PATH)")
    (workdir / "go.mod").write_text("module example.com/generated\n\ngo 1.22\n")
    (workdir / "models.go").write_text(code)
    result = subprocess.run(
        [go, "vet", "./..."], cwd=workdir, capture_output=True, text=True, check=False
    )
    assert result.returncode == 0, result.stderr


@pytest.mark.parametrize(("case", "target"), list(_params()))
def test_generated_code_compiles(case: str, target: str, tmp_path: Path) -> None:
    data = CASES[case]
    if target == "go":
        check_go(quick_generate(data, "go", package_name="models"), tmp_path)
    else:
        check_python(quick_generate(data, "python", style=target))
