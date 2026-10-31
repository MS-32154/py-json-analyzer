from json_explorer.analyzer import analyze_json
from json_explorer.codegen import generate_from_analysis


class TestPerformance:
    """Basic size and depth checks."""

    def test_large_schema_generation(self):
        data = {f"field_{i}": "x" for i in range(100)}

        result = generate_from_analysis(analyze_json(data), "go", None, "Large")
        assert result.success
        assert result.code.count("Field") == 100

    def test_deep_nesting(self):
        data: dict = {"value": "x"}
        for _ in range(10):
            data = {"nested": data}

        result = generate_from_analysis(analyze_json(data), "go", None, "Deep")
        assert result.success

    def test_large_array_is_fully_scanned(self):
        """#11: a key that first appears late in a long array is found."""
        data = [{"a": 1} for _ in range(5000)] + [{"a": 1, "late": "x"}]

        result = generate_from_analysis(analyze_json(data), "go", None, "Root")
        assert "Late *string" in result.code
