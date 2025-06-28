import unittest
from json_explorer.stats import DataStatsAnalyzer


class TestDataStatsAnalyzer(unittest.TestCase):
    def setUp(self):
        self.analyzer = DataStatsAnalyzer()

    def test_empty_data(self):
        """Test analysis of empty/None data"""
        stats = self.analyzer.generate_stats(None)
        self.assertEqual(stats["total_values"], 1)
        self.assertEqual(stats["value_patterns"]["null_count"], 1)
        self.assertEqual(stats["max_depth"], 0)

    def test_simple_dict(self):
        """Test analysis of simple dictionary"""
        data = {"name": "John", "age": 30}
        stats = self.analyzer.generate_stats(data)

        self.assertEqual(stats["total_keys"], 2)
        self.assertEqual(stats["total_values"], 3)  # dict + 2 values
        self.assertEqual(stats["data_types"]["str"], 1)
        self.assertEqual(stats["data_types"]["int"], 1)
        self.assertEqual(stats["max_depth"], 1)

    def test_nested_structure(self):
        """Test analysis of nested data structure"""
        data = {"user": {"profile": {"name": "Alice"}}}
        stats = self.analyzer.generate_stats(data)

        self.assertEqual(stats["max_depth"], 3)
        self.assertEqual(stats["total_keys"], 3)

    def test_list_analysis(self):
        """Test analysis of list structures"""
        data = [1, 2, 3, "hello"]
        stats = self.analyzer.generate_stats(data)

        self.assertEqual(stats["data_types"]["list"], 1)
        self.assertEqual(stats["data_types"]["int"], 3)
        self.assertEqual(stats["data_types"]["str"], 1)
        self.assertEqual(stats["structure_insights"]["array_sizes"][4], 1)

    def test_empty_collections(self):
        """Test handling of empty collections"""
        data = {"empty_list": [], "empty_dict": {}}
        stats = self.analyzer.generate_stats(data)

        self.assertEqual(stats["value_patterns"]["empty_collections"], 2)

    def test_string_analysis(self):
        """Test string length analysis"""
        data = {"short": "hi", "long": "this is a longer string", "empty": ""}
        stats = self.analyzer.generate_stats(data)

        self.assertEqual(stats["value_patterns"]["empty_strings"], 1)
        self.assertEqual(stats["value_patterns"]["string_lengths"]["min"], 0)
        self.assertEqual(stats["value_patterns"]["string_lengths"]["max"], 23)

    def test_numeric_ranges(self):
        """Test numeric value analysis"""
        data = {"values": [1, 5, -3, 10.5]}
        stats = self.analyzer.generate_stats(data)

        self.assertEqual(stats["value_patterns"]["numeric_ranges"]["min"], -3)
        self.assertEqual(stats["value_patterns"]["numeric_ranges"]["max"], 10.5)

    def test_key_naming_patterns(self):
        """Test key naming pattern detection"""
        data = {
            "snake_case_key": 1,
            "camelCaseKey": 2,
            "lowercase": 3,
            "another_snake": 4,
        }
        stats = self.analyzer.generate_stats(data)

        patterns = stats["structure_insights"]["key_naming_patterns"]
        self.assertEqual(patterns["snake_case"], 2)
        self.assertEqual(patterns["camelCase"], 1)
        self.assertEqual(patterns["lowercase"], 1)

    def test_repeated_structures(self):
        """Test detection of repeated structures"""
        data = {
            "users": [
                {"id": 1, "name": "Alice"},
                {"id": 2, "name": "Bob"},
                {"id": 3, "name": "Charlie"},
            ]
        }
        stats = self.analyzer.generate_stats(data)

        # Should detect repeated dict structure with int and str
        repeated = stats["structure_insights"]["repeated_structures"]
        self.assertTrue(len(repeated) > 0)

    def test_complexity_score(self):
        """Test complexity score calculation"""
        simple_data = {"name": "John"}
        complex_data = {
            "level1": {"level2": {"level3": {"data": [1, 2, {"nested": True}]}}}
        }

        simple_stats = self.analyzer.generate_stats(simple_data)
        complex_stats = self.analyzer.generate_stats(complex_data)

        simple_complexity = simple_stats["computed_insights"]["complexity_score"]
        complex_complexity = complex_stats["computed_insights"]["complexity_score"]

        self.assertGreater(complex_complexity, simple_complexity)

    def test_uniformity_assessment(self):
        """Test structure uniformity assessment"""
        uniform_data = [
            {"id": 1, "name": "A"},
            {"id": 2, "name": "B"},
            {"id": 3, "name": "C"},
        ]

        varied_data = [{"id": 1}, {"name": "test", "age": 25}, [1, 2, 3], "string"]

        uniform_stats = self.analyzer.generate_stats(uniform_data)
        varied_stats = self.analyzer.generate_stats(varied_data)

        uniform_uniformity = uniform_stats["computed_insights"]["structure_uniformity"]
        varied_uniformity = varied_stats["computed_insights"]["structure_uniformity"]

        # Uniform data should be more uniform than varied data
        self.assertNotEqual(uniform_uniformity, varied_uniformity)

    def test_path_analysis(self):
        """Test path tracking through nested structures"""
        data = {"user": {"profile": {"name": "Alice"}}}

        stats = self.analyzer.generate_stats(data)
        paths = stats["path_analysis"]

        self.assertIn("user", paths)
        self.assertIn("user.profile", paths)
        self.assertIn("user.profile.name", paths)

    def test_mixed_data_types(self):
        """Test analysis of mixed data types"""
        data = {
            "string": "hello",
            "integer": 42,
            "float": 3.14,
            "boolean": True,
            "null": None,
            "list": [1, 2, 3],
            "dict": {"nested": "value"},
        }

        stats = self.analyzer.generate_stats(data)

        # Check that all types are detected
        types = stats["data_types"]
        self.assertIn("str", types)
        self.assertIn("int", types)
        self.assertIn("float", types)
        self.assertIn("bool", types)
        self.assertIn("NoneType", types)
        self.assertIn("list", types)
        self.assertIn("dict", types)

    def test_large_depth(self):
        """Test handling of deeply nested structures"""
        # Create a deeply nested structure
        data = {"level": 1}
        current = data
        for i in range(2, 12):
            current["nested"] = {"level": i}
            current = current["nested"]

        stats = self.analyzer.generate_stats(data)
        issues = stats["computed_insights"]["data_quality_issues"]

        # Should detect excessive nesting
        self.assertTrue(any("excessive_nesting" in issue for issue in issues))

    def test_reset_functionality(self):
        """Test that reset properly clears previous analysis"""
        data1 = {"test": 1}
        data2 = {"different": "data", "more": "complex"}

        stats1 = self.analyzer.generate_stats(data1)
        stats2 = self.analyzer.generate_stats(data2)

        # Second analysis should not be affected by first
        self.assertEqual(stats2["total_keys"], 2)
        self.assertNotEqual(stats1["total_keys"], stats2["total_keys"])


if __name__ == "__main__":
    unittest.main(verbosity=2)
