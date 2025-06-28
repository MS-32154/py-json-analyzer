from collections import Counter, defaultdict


class DataStatsAnalyzer:
    """Enhanced data structure analyzer with comprehensive statistics and insights."""

    def __init__(self):
        self.reset()

    def reset(self):
        """Reset all statistics for a new analysis."""
        self.stats = {
            "total_keys": 0,
            "total_values": 0,
            "data_types": Counter(),
            "key_frequency": Counter(),
            "max_depth": 0,
            "depth_histogram": Counter(),
            "path_analysis": defaultdict(list),
            "value_patterns": {
                "null_count": 0,
                "empty_strings": 0,
                "empty_collections": 0,
                "numeric_ranges": {"min": float("inf"), "max": float("-inf")},
                "string_lengths": {"min": float("inf"), "max": 0, "avg": 0},
            },
            "structure_insights": {
                "repeated_structures": Counter(),
                "array_sizes": Counter(),
                "key_naming_patterns": Counter(),
            },
        }
        self._string_lengths = []
        self._numeric_values = []
        self._paths = []

    def generate_stats(self, data):
        """
        Generate comprehensive statistics for nested data structures.

        Args:
            data: The data structure to analyze (dict, list, or primitive)

        Returns:
            Dictionary containing detailed statistics and insights
        """
        self.reset()
        self._traverse(data, depth=0, path="root")
        return self._finalize_stats()

    def _traverse(self, obj, depth=0, path="root"):
        """Recursively traverse and analyze the data structure."""
        self.stats["max_depth"] = max(self.stats["max_depth"], depth)
        self.stats["depth_histogram"][depth] += 1
        self._paths.append((path, depth, type(obj).__name__))

        if obj is None:
            self.stats["value_patterns"]["null_count"] += 1
            self.stats["data_types"]["NoneType"] += 1
            self.stats["total_values"] += 1

        elif isinstance(obj, dict):
            self._analyze_dict(obj, depth, path)

        elif isinstance(obj, (list, tuple)):
            self._analyze_sequence(obj, depth, path)

        elif isinstance(obj, str):
            self._analyze_string(obj)

        elif isinstance(obj, (int, float)):
            self._analyze_numeric(obj)

        else:
            self.stats["data_types"][type(obj).__name__] += 1
            self.stats["total_values"] += 1

    def _analyze_dict(self, obj, depth, path):
        """Analyze dictionary objects."""
        if not obj:
            self.stats["value_patterns"]["empty_collections"] += 1

        self.stats["total_keys"] += len(obj)
        self.stats["key_frequency"].update(obj.keys())
        self.stats["data_types"]["dict"] += 1
        self.stats["total_values"] += 1

        # Analyze key naming patterns
        for key in obj.keys():
            if isinstance(key, str):
                if "_" in key:
                    self.stats["structure_insights"]["key_naming_patterns"][
                        "snake_case"
                    ] += 1
                elif any(c.isupper() for c in key[1:]):
                    self.stats["structure_insights"]["key_naming_patterns"][
                        "camelCase"
                    ] += 1
                else:
                    self.stats["structure_insights"]["key_naming_patterns"][
                        "lowercase"
                    ] += 1

        # Track repeated structures
        structure_sig = tuple(sorted(type(v).__name__ for v in obj.values()))
        self.stats["structure_insights"]["repeated_structures"][structure_sig] += 1

        # Recursively analyze values
        for key, val in obj.items():
            new_path = f"{path}.{key}" if path != "root" else key
            self.stats["path_analysis"][new_path].append(type(val).__name__)
            self._traverse(val, depth + 1, new_path)

    def _analyze_sequence(self, obj, depth, path):
        """Analyze list and tuple objects."""
        seq_type = "list" if isinstance(obj, list) else "tuple"

        if not obj:
            self.stats["value_patterns"]["empty_collections"] += 1

        self.stats["data_types"][seq_type] += 1
        self.stats["total_values"] += 1
        self.stats["structure_insights"]["array_sizes"][len(obj)] += 1

        # Analyze sequence contents
        for i, item in enumerate(obj):
            new_path = f"{path}[{i}]"
            self.stats["path_analysis"][new_path].append(type(item).__name__)
            self._traverse(item, depth + 1, new_path)

    def _analyze_string(self, obj):
        """Analyze string values."""
        if not obj:
            self.stats["value_patterns"]["empty_strings"] += 1

        self.stats["data_types"]["str"] += 1
        self.stats["total_values"] += 1
        self._string_lengths.append(len(obj))

        # Update string length stats
        length = len(obj)
        patterns = self.stats["value_patterns"]["string_lengths"]
        patterns["min"] = min(patterns["min"], length)
        patterns["max"] = max(patterns["max"], length)

    def _analyze_numeric(self, obj):
        """Analyze numeric values."""
        self.stats["data_types"][type(obj).__name__] += 1
        self.stats["total_values"] += 1
        self._numeric_values.append(obj)

        # Update numeric range stats
        ranges = self.stats["value_patterns"]["numeric_ranges"]
        ranges["min"] = min(ranges["min"], obj)
        ranges["max"] = max(ranges["max"], obj)

    def _finalize_stats(self):
        """Finalize statistics with computed averages and insights."""
        # Calculate string length average
        if self._string_lengths:
            avg_length = sum(self._string_lengths) / len(self._string_lengths)
            self.stats["value_patterns"]["string_lengths"]["avg"] = round(avg_length, 2)
        else:
            self.stats["value_patterns"]["string_lengths"] = {
                "min": 0,
                "max": 0,
                "avg": 0,
            }

        # Handle numeric ranges edge cases
        if not self._numeric_values:
            self.stats["value_patterns"]["numeric_ranges"] = {"min": None, "max": None}
        elif self.stats["value_patterns"]["numeric_ranges"]["min"] == float("inf"):
            self.stats["value_patterns"]["numeric_ranges"]["min"] = None
            self.stats["value_patterns"]["numeric_ranges"]["max"] = None

        # Add computed insights
        self.stats["computed_insights"] = self._generate_insights()

        return dict(self.stats)

    def _generate_insights(self):
        """Generate high-level insights about the data structure."""
        insights = {
            "complexity_score": self._calculate_complexity(),
            "most_common_type": (
                self.stats["data_types"].most_common(1)[0]
                if self.stats["data_types"]
                else None
            ),
            "structure_uniformity": self._assess_uniformity(),
            "data_quality_issues": self._identify_quality_issues(),
        }

        return insights

    def _calculate_complexity(self):
        """Calculate a complexity score based on depth and variety."""
        type_variety = len(self.stats["data_types"])
        max_depth = self.stats["max_depth"]
        total_elements = self.stats["total_values"]

        complexity = (type_variety * 2) + (max_depth * 3) + (total_elements // 10)
        return min(complexity, 100)

    def _assess_uniformity(self):
        """Assess how uniform the data structure is."""
        if not self.stats["structure_insights"]["repeated_structures"]:
            return "highly_varied"

        most_common_count = self.stats["structure_insights"][
            "repeated_structures"
        ].most_common(1)[0][1]
        total_structures = sum(
            self.stats["structure_insights"]["repeated_structures"].values()
        )

        uniformity_ratio = most_common_count / total_structures

        if uniformity_ratio > 0.8:
            return "highly_uniform"
        elif uniformity_ratio > 0.5:
            return "moderately_uniform"
        else:
            return "highly_varied"

    def _identify_quality_issues(self):
        """Identify potential data quality issues."""
        issues = []

        total_values = self.stats["total_values"]
        if total_values == 0:
            return issues

        null_ratio = self.stats["value_patterns"]["null_count"] / total_values
        empty_ratio = (
            self.stats["value_patterns"]["empty_strings"]
            + self.stats["value_patterns"]["empty_collections"]
        ) / total_values

        if null_ratio > 0.1:
            issues.append(f"high_null_rate ({null_ratio:.1%})")

        if empty_ratio > 0.1:
            issues.append(f"high_empty_rate ({empty_ratio:.1%})")

        if self.stats["max_depth"] > 10:
            issues.append("excessive_nesting")

        return issues

    def print_summary(self, data, detailed=False):
        """Print a formatted summary of the statistics."""
        stats = self.generate_stats(data)

        print("📊 Data Structure Analysis Summary")
        print("=" * 40)
        print(f"Total Values: {stats['total_values']:,}")
        print(f"Total Keys: {stats['total_keys']:,}")
        print(f"Max Depth: {stats['max_depth']}")
        print(f"Complexity Score: {stats['computed_insights']['complexity_score']}/100")
        print(
            f"Structure Uniformity: {stats['computed_insights']['structure_uniformity']}"
        )

        print("\n📈 Data Types Distribution:")
        for dtype, count in stats["data_types"].most_common():
            percentage = (count / stats["total_values"]) * 100
            print(f"  {dtype}: {count:,} ({percentage:.1f}%)")

        if stats["computed_insights"]["data_quality_issues"]:
            print("\n⚠️  Data Quality Issues:")
            for issue in stats["computed_insights"]["data_quality_issues"]:
                print(f"  • {issue}")

        if detailed:
            self._print_detailed_stats(stats)

    def _print_detailed_stats(self, stats):
        """Print detailed statistics."""
        print("\n🔍 Detailed Analysis:")

        if stats["key_frequency"]:
            print("Most Common Keys:")
            for key, count in stats["key_frequency"].most_common(5):
                print(f"  '{key}': {count}")

        print(f"\nDepth Distribution:")
        for depth in sorted(stats["depth_histogram"].keys()):
            count = stats["depth_histogram"][depth]
            print(f"  Depth {depth}: {count} nodes")

        if stats["structure_insights"]["array_sizes"]:
            print("\nArray Size Distribution:")
            for size, count in sorted(
                stats["structure_insights"]["array_sizes"].items()
            ):
                print(f"  Size {size}: {count} arrays")


def generate_stats(data):
    """Generate statistics for nested data structures."""
    analyzer = DataStatsAnalyzer()
    return analyzer.generate_stats(data)


if __name__ == "__main__":
    sample_data = {
        "users": [
            {
                "id": 1,
                "name": "Alice",
                "email": "alice@example.com",
                "profile": {"age": 30, "city": "NYC"},
            },
            {
                "id": 2,
                "name": "Bob",
                "email": None,
                "profile": {"age": 25, "city": "LA"},
            },
            {"id": 3, "name": "", "email": "charlie@example.com", "profile": None},
        ],
        "metadata": {
            "total_count": 3,
            "last_updated": "2025-06-26",
            "settings": {
                "notifications": True,
                "privacy": {"level": "high", "options": ["email", "sms"]},
            },
        },
        "empty_list": [],
        "tags": ["user", "data", "sample"],
    }

    analyzer = DataStatsAnalyzer()
    analyzer.print_summary(sample_data, detailed=True)
