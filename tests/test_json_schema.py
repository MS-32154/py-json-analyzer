"""Tests for the JSON Schema export."""

import json
import sys
from pathlib import Path

import pytest
from json_explorer.json_schema import DRAFT, json_schema
from jsonschema import Draft202012Validator

SAMPLES = Path(__file__).parent.parent / "data_samples"

DOCUMENTS = {
    "object": {"id": 1, "name": "x", "tags": ["a"], "profile": {"age": 3}},
    "array_of_objects": [{"a": 1, "b": "x"}, {"b": "y", "c": None}],
    "nested_arrays": {"m": [[1, 2], []], "g": [[{"id": 1}]]},
    "null_elements": {"vals": [1, None, 2], "objs": [{"a": 1}, None]},
    "mixed": [{"v": 1}, {"v": "x"}, {"v": None}],
    "numbers": [{"n": 1}, {"n": 2.5}],
    "formats": [
        {
            "at": "2024-01-01T10:00:00Z",
            "day": "2024-01-01",
            "dur": "P1D",
            "local": "2024-01-01T10:00:00",
            "clock": "10:30:00",
        }
    ],
    "empty_object": {},
    "empty_array": [],
    "scalar": 42,
    "null": None,
} | {
    p.stem: json.loads(p.read_text(encoding="utf-8"))
    for p in sorted(SAMPLES.glob("*.json"))
}


@pytest.mark.parametrize("name", list(DOCUMENTS))
def test_schema_is_valid_and_accepts_its_source(name: str) -> None:
    data = DOCUMENTS[name]
    schema = json_schema(data, title=name)
    Draft202012Validator.check_schema(schema)
    Draft202012Validator(schema).validate(data)  # raises if the data doesn't fit


def schema_of(data):
    return json_schema(data)


def item_properties(data) -> dict:
    return schema_of(data)["items"]["properties"]


class TestShape:
    def test_header(self):
        schema = json_schema({"a": 1}, title="Thing")
        assert schema["$schema"] == DRAFT
        assert schema["title"] == "Thing"

    def test_array_root_stays_an_array(self):
        schema = schema_of([{"a": 1}])
        assert schema["type"] == "array"
        assert schema["items"]["type"] == "object"

    def test_required_only_when_always_present(self):
        items = schema_of([{"a": 1, "b": 2}, {"a": 3}])["items"]
        assert items["required"] == ["a"]

    def test_null_is_allowed_but_key_still_required(self):
        """#23 semantics: present-but-null is not optional."""
        items = schema_of([{"e": None}, {"e": "x"}])["items"]
        assert items["properties"]["e"]["type"] == ["string", "null"]
        assert items["required"] == ["e"]

    def test_int_and_float_are_number(self):
        assert item_properties([{"n": 1}, {"n": 2.5}])["n"]["type"] == "number"

    def test_integers_stay_integer(self):
        assert item_properties([{"n": 1}, {"n": 2}])["n"]["type"] == "integer"

    def test_mixed_lists_all_types(self):
        props = item_properties([{"v": 1}, {"v": "x"}, {"v": None}])
        assert props["v"]["type"] == ["integer", "string", "null"]

    def test_nested_arrays(self):
        props = schema_of({"m": [[1]]})["properties"]
        assert props["m"]["items"]["items"]["type"] == "integer"

    def test_empty_array_items_unconstrained(self):
        assert schema_of({"tags": []})["properties"]["tags"]["items"] == {}

    def test_additional_properties_allowed(self):
        assert "additionalProperties" not in schema_of({"a": 1})


class TestFormats:
    @pytest.mark.parametrize(
        ("value", "fmt"),
        [
            ("2024-01-01T10:00:00Z", "date-time"),
            ("2024-01-01", "date"),
            ("PT4H", "duration"),
        ],
    )
    def test_json_schema_formats(self, value, fmt):
        assert schema_of({"v": value})["properties"]["v"]["format"] == fmt

    @pytest.mark.parametrize("value", ["10:30:00", "2024-01-01T10:00:00"])
    def test_no_format_where_json_schema_needs_an_offset(self, value):
        prop = schema_of({"v": value})["properties"]["v"]
        assert "format" not in prop
        assert "offset" in prop["description"]

    def test_plain_string(self):
        assert schema_of({"v": "March"})["properties"]["v"] == {"type": "string"}


class TestCli:
    @pytest.fixture
    def run(self, monkeypatch):
        from json_explorer.main import main

        def _run(*argv):
            monkeypatch.setattr(sys, "argv", ["json_explorer", *map(str, argv)])
            return main()

        return _run

    def test_stdout_is_raw_json(self, run, capsys):
        assert run(SAMPLES / "003_sample_project.json", "--json-schema") == 0
        schema = json.loads(capsys.readouterr().out)
        assert schema["title"] == "003_sample_project"

    def test_output_file(self, run, tmp_path, capsys):
        target = tmp_path / "s.json"
        sample = SAMPLES / "001_sample_project.json"
        assert (
            run(sample, "--json-schema", "--output", target, "--root-name", "Projects")
            == 0
        )
        assert json.loads(target.read_text(encoding="utf-8"))["title"] == "Projects"
        out = capsys.readouterr()
        assert out.out == ""
        assert "saved" in out.err


@pytest.mark.parametrize(
    "bad",
    [
        [{"id": "one", "tags": []}],  # wrong type
        [{"tags": []}],  # required key missing
        [{"id": 1, "tags": [1]}],  # wrong item type
        {"id": 1},  # object instead of array
    ],
)
def test_schema_rejects_data_of_another_shape(bad) -> None:
    schema = json_schema([{"id": 1, "tags": ["a"]}, {"id": 2, "tags": []}])
    assert not Draft202012Validator(schema).is_valid(bad)
