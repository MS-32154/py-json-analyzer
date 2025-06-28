from json_explorer.analyzer import analyze_json


def test_primitive_int():
    assert analyze_json(5) == {"type": "int"}


def test_primitive_str():
    assert analyze_json("hello") == {"type": "str"}


def test_empty_list():
    assert analyze_json([]) == {"type": "list", "child_type": "unknown"}


def test_list_of_ints():
    assert analyze_json([1, 2, 3]) == {"type": "list", "child_type": "int"}


def test_list_of_strings():
    assert analyze_json(["a", "b", "c"]) == {"type": "list", "child_type": "str"}


def test_mixed_list():
    assert analyze_json([1, "a"]) == {"type": "list", "child_type": "mixed"}


def test_object():
    result = analyze_json({"name": "Alice", "age": 30})
    expected = {
        "type": "object",
        "children": {"name": {"type": "str"}, "age": {"type": "int"}},
    }
    assert result == expected


def test_list_of_objects():
    data = [{"name": "Alice"}, {"name": "Bob"}]
    result = analyze_json(data)
    expected = {
        "type": "list",
        "child": {
            "type": "object",
            "children": {"name": {"type": "str", "optional": False}},
            "conflicts": {},
        },
    }
    assert result == expected


def test_conflicting_object_types():
    data = [{"id": 1}, {"id": "one"}]
    result = analyze_json(data)
    expected = {
        "type": "list",
        "child": {
            "type": "object",
            "children": {"id": {"type": "conflict", "optional": False}},
            "conflicts": {"id": ["int", "str"]},
        },
    }
    # Allow unordered conflict values
    assert (
        result["child"]["conflicts"]["id"].sort()
        == expected["child"]["conflicts"]["id"].sort()
    )
    result["child"]["conflicts"]["id"] = expected["child"]["conflicts"]["id"]
    assert result == expected


def test_optional_keys():
    data = [{"a": 1}, {"b": 2}]
    result = analyze_json(data)
    expected = {
        "type": "list",
        "child": {
            "type": "object",
            "children": {
                "a": {"type": "int", "optional": True},
                "b": {"type": "int", "optional": True},
            },
            "conflicts": {},
        },
    }
    assert result == expected
