"""Tests for identifier naming: word splitting, language rules, name plans."""

import pytest
from json_explorer.analyzer import analyze_json
from json_explorer.codegen.core.naming import (
    plan_names,
    split_words,
    to_pascal_case,
    to_snake_case,
    unique_name,
)
from json_explorer.codegen.core.schema import (
    convert_analyzer_output,
    extract_all_schemas,
    singularize,
    type_name_for_key,
)
from json_explorer.codegen.languages.go.naming import (
    go_identifier,
    go_json_tag,
    is_valid_json_tag_name,
)
from json_explorer.codegen.languages.python.naming import (
    is_plain_key,
    python_class_name,
    python_field_name,
)


class TestWordSplitting:
    @pytest.mark.parametrize(
        ("name", "words"),
        [
            ("userName", ("user", "Name")),
            ("UserName", ("User", "Name")),
            ("user_name", ("user", "name")),
            ("user-name", ("user", "name")),
            ("userID", ("user", "ID")),
            ("HTTPServer", ("HTTP", "Server")),
            ("XMLHttpRequest", ("XML", "Http", "Request")),
            ("iOSVersion", ("i", "OS", "Version")),
            ("user2FA", ("user2", "FA")),
            ("$ref", ("ref",)),
            ("café", ("cafe",)),
            ("名前", ("名前",)),
            ("", ()),
        ],
    )
    def test_split_words(self, name, words):
        assert split_words(name) == words

    def test_snake_and_pascal(self):
        assert to_snake_case("XMLHttpRequest") == "xml_http_request"
        assert to_pascal_case("first-name") == "FirstName"
        assert to_snake_case("naïve_count") == "naive_count"


class TestUniqueName:
    def test_numbers_collisions(self):
        used: set[str] = set()
        assert [unique_name("Address", used) for _ in range(3)] == [
            "Address",
            "Address2",
            "Address3",
        ]

    def test_separator(self):
        used = {"name"}
        assert unique_name("name", used, "_") == "name_2"


class TestGoNaming:
    @pytest.mark.parametrize(
        ("key", "ident"),
        [
            ("user_id", "UserId"),
            ("type", "Type"),  # exported names never clash with keywords
            ("string", "String"),
            ("123abc", "Field123abc"),  # #6: exported, not _123abc
            ("名前", "Field"),
            ("café", "Cafe"),
        ],
    )
    def test_identifier(self, key, ident):
        assert go_identifier(key) == ident

    @pytest.mark.parametrize(
        ("key", "valid"),
        [
            ("name", True),
            ("user-id", True),
            ("@type", True),
            ("名前", True),
            ('q"k', False),
            ("a,b", False),
            ("back\\slash", False),
            ("it's", False),
            ("", False),
        ],
    )
    def test_valid_tag_names(self, key, valid):
        assert is_valid_json_tag_name(key) is valid

    def test_tag_escaping(self):
        assert go_json_tag("name", omitempty=False) == '`json:"name"`'
        assert go_json_tag("id", omitempty=True) == '`json:"id,omitempty"`'


class TestPythonNaming:
    @pytest.mark.parametrize(
        ("key", "ident"),
        [
            ("userName", "user_name"),
            ("id", "id"),  # builtins are fine as attribute names
            ("type", "type"),
            ("class", "class_"),  # keyword
            ("str", "str_"),  # would shadow the annotation name
            ("123abc", "field_123abc"),  # #6: never a leading underscore
            ("_private", "private"),
            ("名前", "名前"),  # valid Python identifier
        ],
    )
    def test_field_name(self, key, ident):
        assert python_field_name(key) == ident

    def test_pydantic_reserved(self):
        assert python_field_name("json", pydantic=True) == "json_"
        assert python_field_name("model_id", pydantic=True) == "field_model_id"
        assert python_field_name("json") == "json"

    @pytest.mark.parametrize(
        ("name", "ident"),
        [("user_address", "UserAddress"), ("Class", "Class"), ("Field", "Field_")],
    )
    def test_class_name(self, name, ident):
        assert python_class_name(name) == ident

    def test_plain_keys(self):
        assert is_plain_key("userId")
        assert not is_plain_key("first-name")
        assert not is_plain_key("class")


class TestTypeNames:
    @pytest.mark.parametrize(
        ("word", "singular"),
        [
            ("users", "user"),
            ("categories", "category"),
            ("addresses", "address"),
            ("boxes", "box"),
            ("status", "status"),
            ("data", "data"),
            ("analysis", "analysis"),
        ],
    )
    def test_singularize(self, word, singular):
        assert singularize(word) == singular

    def test_type_name_for_key(self):
        assert type_name_for_key("team_lead") == "TeamLead"
        assert type_name_for_key("projects", item=True) == "Project"
        assert type_name_for_key("data", item=True) == "DataItem"

    def test_same_key_at_two_paths_gets_two_types(self):
        data = {"billing": {"address": {"a": 1}}, "shipping": {"address": {"b": "x"}}}
        schemas = extract_all_schemas(convert_analyzer_output(analyze_json(data)))
        assert {"Address", "Address2"} <= set(schemas)
        assert schemas["Address"] is not schemas["Address2"]


class TestNamePlan:
    def test_references_match_declarations(self):
        data = {"name": "x", "address": {"name": "y"}}
        schemas = extract_all_schemas(convert_analyzer_output(analyze_json(data)))
        plan = plan_names(
            schemas.values(),
            type_identifier=go_identifier,
            field_identifier=go_identifier,
        )
        root, address = schemas["Root"], schemas["Address"]
        address_field = next(f for f in root.fields if f.original_name == "address")
        assert plan.type_name(address_field.nested_schema) == plan.type_name(address)
        # same key in two structs: no cross-struct numbering (#1)
        assert {plan.field_name(f) for f in root.fields} == {"Name", "Address"}
        assert {plan.field_name(f) for f in address.fields} == {"Name"}

    def test_keys_mapping_to_one_identifier_are_numbered(self):
        data = {"user_name": 1, "userName": 2, "user-name": 3}
        schemas = extract_all_schemas(convert_analyzer_output(analyze_json(data)))
        plan = plan_names(
            schemas.values(),
            type_identifier=python_class_name,
            field_identifier=python_field_name,
            field_separator="_",
        )
        names = [plan.field_name(f) for f in schemas["Root"].fields]
        assert names == ["user_name", "user_name_2", "user_name_3"]
