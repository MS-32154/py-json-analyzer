"""Compile checks: generated code must be valid for the real toolchain.

The other codegen tests only check that strings appear in the output, which
let broken code through. These tests feed the output to the language itself:

- Python: the module is executed, Pydantic models are rebuilt, and every
  class's annotations are resolved with ``typing.get_type_hints``.
- Go: the file is type-checked with ``go vet`` (skipped when Go is missing).

Known bugs used to be tracked here as strict xfails; Phase 2 fixed the last
of them (#1, #6, #7, #19), so every case must now pass.
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


def _params():
    for case in CASES:
        for target in TARGETS:
            yield pytest.param(case, target, id=f"{case}-{target}")


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


def test_typeddict_keeps_json_keys() -> None:
    """A TypedDict describes the dict as-is, so its keys must be the JSON keys."""
    data = {"userID": 1, "first-name": "Ada", "type": "admin"}
    namespace: dict[str, typing.Any] = {"__name__": "generated"}
    exec(quick_generate(data, "python", style="typeddict"), namespace)
    root = namespace["Root"]
    assert set(typing.get_type_hints(root)) == set(data)
