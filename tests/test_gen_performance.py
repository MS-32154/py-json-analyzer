from json_explorer.codegen import generate_from_analysis


class TestPerformance:
    """Basic performance tests."""

    def test_large_schema_generation(self):
        # Generate large analyzer result
        children = {
            f"field_{i}": {"type": "str", "optional": False} for i in range(100)
        }

        large_result = {"type": "object", "children": children, "conflicts": {}}

        result = generate_from_analysis(large_result, "go", None, "Large")
        assert result.success
        assert result.code.count("Field") == 100

    def test_deep_nesting(self):
        # Create deeply nested structure
        current = {"type": "str", "optional": False}

        for i in range(10):
            current = {
                "type": "object",
                "children": {"nested": current},
                "optional": False,
            }

        nested_result = {
            "type": "object",
            "children": {"root": current},
            "conflicts": {},
        }

        result = generate_from_analysis(nested_result, "go", None, "Deep")
        assert result.success
